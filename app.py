import os
import uuid
from flask import Flask, render_template, redirect, url_for, request, flash
import pigpio
import time
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.utils import secure_filename
from models import Pet, Task, Feed, session  # Import Feed model
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Folder for storing uploaded images
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed image file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.start()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def servo(pet_id):
    print("Starting servo operation")
    pi = pigpio.pi()
    pi.set_mode(18, pigpio.OUTPUT)

    # Rotate by 90 degrees
    pi.set_servo_pulsewidth(18, 1000)
    time.sleep(0.4)

    # Return to initial position
    pi.set_servo_pulsewidth(18, 2000)
    pi.stop()

    # Update experience and level, log feeding time
    pet = session.query(Pet).get(pet_id)
    if pet:
        pet.feed_count += 1
        pet.experience += 1
        pet.update_level()
        new_feed = Feed(pet_id=pet_id, feed_time=datetime.utcnow())
        session.add(new_feed)
        session.commit()
        print(f"{pet.name} bol nakŕmený a získal nový úroveň: {pet.level}.")

@app.route('/feed/<int:pet_id>', methods=['POST'])
def feed(pet_id):
    pet = session.query(Pet).get(pet_id)
    
    if pet:
        servo(pet_id)
        flash(f"{pet.name} bol nakŕmený a teraz má úroveň: {pet.level}.", 'success')
    else:
        flash("Zvieratko nebolo nájdené.", 'error')
    
    return redirect(url_for('pet_tasks', pet_id=pet_id))



@app.route('/')
def index():
    pets = session.query(Pet).all()  # Fetch all pets from the database
    return render_template('index.html', pets=pets)

@app.route('/create_pet', methods=['GET', 'POST'])
def create_pet():
    if request.method == 'POST':
        name = request.form['name']
        age = int(request.form['age'])
        photo = None

        # Check if a file was uploaded and is valid
        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                # Ensure the upload folder exists
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])

                # Generate a unique filename
                unique_filename = f"{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}"
                photo = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(photo)

        # Create a new pet
        new_pet = Pet(name=name, age=age, photo=photo)
        session.add(new_pet)
        session.commit()

        return redirect(url_for('index'))
    return render_template('create_pet.html')

@app.route('/pet/<int:pet_id>')
def pet_tasks(pet_id):
    pet = session.query(Pet).get(pet_id)
    return render_template('pet_tasks.html', pet=pet)

@app.route('/schedule/<int:pet_id>', methods=['GET', 'POST'])
def schedule(pet_id):
    if request.method == 'POST':
        feed_time = request.form['time']
        hour, minute = map(int, feed_time.split(':'))

        # Create a task name based on the time
        task_name = f"{hour:02}:{minute:02}"

        # Check for an existing task with the same name for this pet
        existing_task = session.query(Task).filter_by(name=task_name, pet_id=pet_id).first()
        if existing_task:
            flash(f"Task at {task_name} already exists for this pet.")
            return redirect(url_for('schedule', pet_id=pet_id))

        # Create a new task
        new_task = Task(name=task_name, hour=hour, minute=minute, pet_id=pet_id)
        session.add(new_task)
        session.commit()

        # Add the task to the scheduler, passing pet_id to the servo function
        scheduler.add_job(servo, 'cron', hour=hour, minute=minute, args=[pet_id], id=f"{pet_id}-{task_name}")
        flash(f"Scheduled task at {task_name}")
        return redirect(url_for('pet_tasks', pet_id=pet_id))
    return render_template('schedule.html', pet_id=pet_id)


@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    task = session.query(Task).get(task_id)

    if task:
        # Remove the task from the scheduler if it exists
        if scheduler.get_job(f"{task.pet_id}-{task.name}"):
            scheduler.remove_job(f"{task.pet_id}-{task.name}")

        # Delete the task from the database
        session.delete(task)
        session.commit()
        flash("Task deleted successfully")

    return redirect(url_for('pet_tasks', pet_id=task.pet_id))

@app.route('/delete_pet/<int:pet_id>', methods=['POST'])
def delete_pet(pet_id):
    pet = session.query(Pet).get(pet_id)
    
    if pet:
        # Delete all tasks related to this pet
        tasks = session.query(Task).filter_by(pet_id=pet.id).all()
        for task in tasks:
            # Remove the task from the scheduler
            if scheduler.get_job(f"{task.pet_id}-{task.name}"):
                scheduler.remove_job(f"{task.pet_id}-{task.name}")
            session.delete(task)
        
        # Delete the pet
        session.delete(pet)
        session.commit()
        flash(f"Питомец {pet.name} был успешно удален.", 'success')
    else:
        flash("Питомец не найден.", 'error')
    
    return redirect(url_for('index'))

@app.route('/statistics/<int:pet_id>')
def statistics(pet_id):
    pet = session.query(Pet).get(pet_id)
    
    if pet:
        period = request.args.get('period', 'week')  # By default, display statistics for the week
        feed_count = pet.feed_statistics(period)
        return render_template('statistics.html', pet=pet, feed_count=feed_count, period=period)
    else:
        flash("Zvieratko nebolo nájdené.", 'error')
        return redirect(url_for('index'))


if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=80)  # Use a different port to avoid conflicts
    finally:
        scheduler.shutdown()
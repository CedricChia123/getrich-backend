import time
import subprocess
from flask import Flask

app = Flask(__name__)

# Function to execute Python files one after another
def execute_files():
    subprocess.run(['python', 'scrape.py'])
    subprocess.run(['python', 'sentiment.py'])

# Route to trigger the execution of Python files
@app.route('/execute', methods=['GET'])
def execute():
    execute_files()
    return 'Python files executed successfully!'

if __name__ == '__main__':
    while True:
        start_time = time.time()
        execute_files()
        end_time = time.time()
        time_taken = end_time - start_time
        print("Time taken for sentiment analysis is", time_taken, "seconds.")
        # Repeat every 1 hour
        time.sleep(3600)
        print("Executing next cycle")

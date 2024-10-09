from flask import Flask, render_template, request, redirect, url_for, send_file
import pandas as pd
import os
from dotenv import load_dotenv
import csv
import google.generativeai as genai
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'

# Convert Excel file to CSV
def excel_to_csv(excel_file_path):
    df = pd.read_excel(excel_file_path)
    csv_file_path = os.path.join(UPLOAD_FOLDER, 'converted.csv')
    df.to_csv(csv_file_path, index=False, sep=';', encoding='utf-8-sig')
    return csv_file_path

# Send the text prompt to the Gemini 1.5 API and get CSV response
def send_to_gemini(prompt, original_filename):
    load_dotenv()
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,
        ),
    )
    # Write the response text into a csv file
    csv_file_name = f"{os.path.splitext(original_filename)[0]}_Analyse.csv"
    csv_output_path = os.path.join(UPLOAD_FOLDER, csv_file_name)
    with open(csv_output_path, 'w', encoding='utf-8-sig') as textfile:
        textfile.write(response.text)
    return csv_output_path

# Convert CSV back to Excel (if needed, comment out the function call below)
def csv_to_excel(csv_file_path, original_filename):
    df = pd.read_csv(csv_file_path, encoding='utf-8-sig', sep=';', on_bad_lines='skip')
    excel_file_name = f"{os.path.splitext(original_filename)[0]}_Analyse.xlsx"
    excel_file_path = os.path.join(UPLOAD_FOLDER, excel_file_name)
    df.to_excel(excel_file_path, index=False)
    return excel_file_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files or not request.form.get('text'):
        return 'No file or text provided!', 400

    file = request.files['file']
    text_input = request.form.get('text')

    if file and text_input:
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Convert Excel to CSV if needed
        if file_path.lower().endswith(('.xls', '.xlsx')):
            csv_file_path = excel_to_csv(file_path)
        else:
            csv_file_path = file_path

        # Read CSV content to append to text
        with open(csv_file_path, 'r') as f:
            csv_content = f.read()

        # Configuration: Instruction for the AI model to constrain output to csv-formatted data only
        configuration = "\nGib die bearbeitete Tabelle bitte im csv-Format (mit ; statt , als Trennzeichen) aus. Bitte benutze keine "". Bitte gib nur die Tabelle aus, keine zusätzlichen Erklärungen oder Einleitungssätze. Nach dem Delimiter ### findest du die Input-Tabelle im csv-Format\n###\n"

        # Append configuration and CSV content to the input text
        prompt = text_input + configuration + csv_content

        # Send prompt to Gemini 1.5 flash API and get the processed CSV
        csv_output_path = send_to_gemini(prompt, file.filename)

        # Convert the output CSV to Excel (comment out this function call if the output should be in xlsx format)
        # excel_output_path = csv_to_excel(csv_output_path, file.filename)

        # Render the download button for the processed Excel file
        return render_template('index.html', download_link=csv_output_path)

    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def download_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(file_path, as_attachment=True)

@app.route('/cleanup')
def cleanup_and_redirect():
    # Delete the uploads folder: No user data remains on the server
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)

    # Redirect back to the home page
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

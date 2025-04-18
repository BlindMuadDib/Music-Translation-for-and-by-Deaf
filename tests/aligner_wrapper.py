"""
Wrapper for  Kubernetes to run specific codes against the Montreal Forced Aligner Docker image
MFA repository: https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner
Licensed under MIT license.

ARGS:
    lyrics transcript filepath and vocal stem filepath

RETURNS:
    Alignment data in JSON format
"""
import subprocess
import os
import shutil
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

CORPUS_DIR = "/app/data/corpus"
OUTPUT_DIR = "/app/data/aligned"

@app.route('/align', methods=['POST'])
def align():
    """Main function of the wrapper"""
    logging.debug("Received /align request")
    data = request.get_json()
    if not data or 'vocal_stem_path' not in data or 'lyrics_file_path' not in data:
        return jsonify({'error': 'vocal_stem_path or lyrics_file_path missing'}), 400

    # Extract filenames and create matching base names
    vocal_stem_path = request.json['vocal_stem_path']
    lyrics_file_path = request.json['lyrics_file_path']
    base_name = os.path.splitext(os.path.basename(vocal_stem_path))[0]
    # Copy files to corpus directory with matching base names
    corpus_audio_path = os.path.join(CORPUS_DIR, f"{base_name}.wav")
    corpus_lyrics_path = os.path.join(CORPUS_DIR, f"{base_name}.txt")
    json_output_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(CORPUS_DIR, exist_ok=True)
        shutil.copy(vocal_stem_path, corpus_audio_path)
        shutil.copy(lyrics_file_path, corpus_lyrics_path)

        # Debugging statements
        print(f"Copied audio to: {corpus_audio_path}")
        print(f"Copied lyrics to {corpus_lyrics_path}")

        # Download the models and dictionaries
        subprocess.run(
            ["mfa", "model", "download", "acoustic", "english_us_arpa"],
            check=True
        )
        subprocess.run(
            ["mfa", "model", "download", "dictionary", "english_us_arpa"],
        check=True
        )

        # Validate the corpus
        validation_result = subprocess.run(
            ["mfa", "validate", CORPUS_DIR,
            "english_us_arpa", "english_us_arpa"],
            capture_output=True, text=True, check=True
        )

        if validation_result.returncode != 0:
            return jsonify({'error': f"Corpus validation failed: {validation_result.stderr}"}), 500

        # Perform alignment, set output format to JSON
        alignment_result = subprocess.run(
            ["mfa", "align",
             "--output_format", "json",
             CORPUS_DIR,
            "english_us_arpa", "english_us_arpa", OUTPUT_DIR],
            capture_output=True, text=True, check=False
        )
        logging.debug(f"Align stdout (initial): {alignment_result.stdout}")
        logging.debug(f"Align stderr (initial): {alignment_result.stderr}")

        # If alignment fails on intial attempt, increase beam size
        # Solves failed alingment for most songs
        if alignment_result.returncode != 0:
            print("Retry alignment ...")
            retry_result = subprocess.run(
                ["mfa", "align",
                 "--output_format", "json",
                 CORPUS_DIR,
                "english_us_arpa", "english_us_arpa", OUTPUT_DIR,
                "--beam", "100", "--retry_beam", "400"],
                    capture_output=True, text=True, check=False
            )
            logging.debug(f"Align stdout (retry): {retry_result.stdout}")
            logging.debug(f"Align stderr (retry): {retry_result.stderr}")

            if retry_result.returncode != 0:
                return jsonify({'error': f"Alignment failed: {retry_result.stderr}"}), 500
            alignment_result = retry_result
            logging.debug(f"Alignment result: {alignment_result}")
        print(f"JSON export likely successful to {json_output_path}")
        return jsonify({'alignment_file_path': json_output_path}), 200

    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e}")
        logging.error(f"Subprocess stdout: {e.stdout}")
        logging.error(f"Subprocess stderr: {e.stderr}")
        error_message = e.stderr if e.stderr else str(e)
        return jsonify({'error': error_message}), 500
    except FileNotFoundError as e:
        logging.error(f"File not found error: {e}")
        return jsonify({'error': f"File not found: {e}"}), 404
    except ValueError as e:
        logging.error(f"Value error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e: # pylint: disable=broad-except
        logging.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    logging.info("Flask app starting on port 24725...")
    app.run(debug=False, host='0.0.0.0', port=24725)

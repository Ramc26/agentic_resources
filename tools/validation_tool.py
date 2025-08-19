import os
import requests
from dotenv import load_dotenv

load_dotenv()
def validate_contact(input_string: str, validation_type: str) -> str:
    """Validates a phone number or an email address using the API-Ninjas service.
    Input should be a string containing the phone number (e.g., '+12065550100') or email (e.g., 'test@example.com'),
    and the validation_type should be either 'phone' or 'email'.
    """
    api_key = os.getenv("API_NINJAS_KEY")
    if not api_key:
        return "Error: API-Ninjas API key not found in environment variables."

    if validation_type == 'phone':
        api_url = 'https://api.api-ninjas.com/v1/validatephone?number={}'.format(input_string)
    elif validation_type == 'email':
        api_url = 'https://api.api-ninjas.com/v1/validateemail?email={}'.format(input_string)
    else:
        return "Error: Invalid validation_type. Must be 'phone' or 'email'."

    try:
        response = requests.get(api_url, headers={'X-Api-Key': api_key})
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error during API call: {e}"

import requests

def send_prediction_to_api(prediction_data, api_endpoint):
    """
    Send prediction directly to HF Spaces API via HTTP POST
    
    Args:
        prediction_data (dict): Prediction payload
        api_endpoint (str): HF Spaces API URL
    
    Returns:
        bool: True if successful
    """
    try:
        response = requests.post(
            api_endpoint,
            json=prediction_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 201:
            print(f"✓ Sent to API: {prediction_data['tomato_id']}")
            return True
        else:
            print(f"✗ API error ({response.status_code}): {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        print(f"API timeout")
        return False
    except requests.exceptions.ConnectionError:
        print(f"Connection error - check internet")
        return False
    except Exception as e:
        print(f"Error sending to API: {e}")
        return False
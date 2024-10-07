from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# In-memory session
sessions = {}

@csrf_exempt
def ussd(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON request body
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Extract necessary USSD fields from the request
        ussd_id = data.get('USERID', '')
        msisdn = data.get('MSISDN', '')
        user_data = data.get('USERDATA', '')
        msgtype = data.get('MSGTYPE', True)  # True if first request, False if subsequent
        session_id = data.get('SESSIONID', '')  # Extract session ID from the incoming request

        if not session_id:
            return JsonResponse({'error': 'SESSIONID is missing'}, status=400)

        # Retrieve or initialize the session based on the provided SESSIONID
        if session_id not in sessions:
            sessions[session_id] = {'screen': 1, 'feeling': '', 'reason': ''}

        session = sessions[session_id]

        # Initial request (first screen)
        if msgtype:
            # Screen 1: Ask how the user is feeling
            msg = f"Welcome to {ussd_id} USSD Application.\nHow are you feeling?\n\n1. Feeling fine\n2. Feeling frisky\n3. Not well"
            session['screen'] = 1  # Set the screen to 1
            response_data = {
                "USERID": ussd_id,
                "MSISDN": msisdn,
                "MSG": msg,
                "MSGTYPE": True
            }

        else:
            # Handle the interaction based on the current screen
            if session['screen'] == 1:
                # Process the user's choice from Screen 1
                if user_data == '1':
                    session['feeling'] = 'Feeling fine'
                elif user_data == '2':
                    session['feeling'] = 'Feeling frisky'
                elif user_data == '3':
                    session['feeling'] = 'Not well'
                else:
                    # Invalid input, repeat Screen 1
                    msg = "Invalid choice. How are you feeling?\n\n1. Feeling fine\n2. Feeling frisky\n3. Not well"
                    response_data = {
                        "USERID": ussd_id,
                        "MSISDN": msisdn,
                        "MSG": msg,
                        "MSGTYPE": True
                    }
                    return JsonResponse(response_data)

                # Move to Screen 2: Ask why the user feels that way
                msg = f"Why are you {session['feeling']}?\n1. Money\n2. Relationship\n3. A lot"
                session['screen'] = 2  # Set the screen to 2
                response_data = {
                    "USERID": ussd_id,
                    "MSISDN": msisdn,
                    "MSG": msg,
                    "MSGTYPE": True
                }

            elif session['screen'] == 2:
                # Process the user's choice from Screen 2
                if user_data == '1':
                    session['reason'] = 'because of money'
                elif user_data == '2':
                    session['reason'] = 'because of relationship'
                elif user_data == '3':
                    session['reason'] = 'because of a lot'
                else:
                    # Invalid input, repeat Screen 2
                    msg = f"Invalid choice. Why are you {session['feeling']}?\n1. Money\n2. Relationship\n3. A lot"
                    response_data = {
                        "USERID": ussd_id,
                        "MSISDN": msisdn,
                        "MSG": msg,
                        "MSGTYPE": True
                    }
                    return JsonResponse(response_data)

                # Move to Screen 3: Summarize the user's input
                msg = f"You are {session['feeling']} {session['reason']}."
                response_data = {
                    "USERID": ussd_id,
                    "MSISDN": msisdn,
                    "MSG": msg,
                    "MSGTYPE": False  # Final message, end session
                }

                # End the session after Screen 3
                del sessions[session_id]  # Remove session after the interaction is completed

        return JsonResponse(response_data)

    # If request method is not POST, return a 405 Method Not Allowed error
    return JsonResponse({'error': 'Method not allowed'}, status=405)

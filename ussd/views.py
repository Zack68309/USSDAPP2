import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Set up logging to display request and response in the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory session storage
sessions = {}


@csrf_exempt
def ussd(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON request body
            data = json.loads(request.body.decode('utf-8'))
            logger.info(f"Incoming request data: {data}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in the request")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Extract necessary fields from the request
        ussd_id = data.get('USERID')
        msisdn = data.get('MSISDN')
        user_data = data.get('USERDATA')
        msgtype = data.get('MSGTYPE')  # True if first request, False if subsequent
        session_id = data.get('SESSIONID')

        # Ensure session ID is present
        if not session_id:
            logger.error("SESSIONID is missing in the request")
            return JsonResponse({'error': 'SESSIONID is missing'}, status=400)

        # Clean up and split user_data by '*'
        parts = [part.strip('#') for part in user_data.split('*') if part]
        logger.info(f"Parsed USSD data: {parts}")

        # Initialize a new session if it doesn't exist
        if session_id not in sessions:
            sessions[session_id] = {'screen': 1, 'feeling': '', 'reason': ''}
            logger.info(f"New session started with ID: {session_id}")

        session = sessions[session_id]
        logger.info(f"Current session state: {session}")

        # Logic 1: Standard Flow (*920*1806#)
        if len(parts) == 2 and parts[0] == '920' and parts[1] == '1806':
            if msgtype:  # First request after dialing *920*1806#
                msg = "Welcome to USSD Application\n\nHow are you feeling?\n\n1. Feeling fine\n2. Feeling frisky\n3. Not well"
                session['screen'] = 1
                response_data = {
                    "USERID": ussd_id,
                    "MSISDN": msisdn,
                    "MSG": msg,
                    "MSGTYPE": True
                }
                logger.info(f"Response: {response_data}")
                return JsonResponse(response_data)
            else:
                # If it's not the first message, treat it as invalid since we expect a choice at this point
                logger.error("Invalid choice in Screen 1 for direct access")
                return JsonResponse({'error': 'Invalid choice in Screen 1'}, status=400)

        # Handling user input after initial dialing (*920*1806#) in Screen 1
        if session['screen'] == 1 and len(parts) == 1:  # Expecting a response like '1', '2', '3'
            logger.info(f"User input for Screen 1: {user_data}")
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
                logger.info(f"Response: {response_data}")
                return JsonResponse(response_data)

            # Move to Screen 2: Ask why the user feels that way
            msg = f"Why are you {session['feeling']}?\n1. Money\n2. Relationship\n3. A lot"
            session['screen'] = 2
            response_data = {
                "USERID": ussd_id,
                "MSISDN": msisdn,
                "MSG": msg,
                "MSGTYPE": True
            }
            logger.info(f"Response: {response_data}")
            return JsonResponse(response_data)

        # Handling user input for Screen 2
        if session['screen'] == 2 and len(parts) == 1:  # Expecting a response for why they feel that way
            logger.info(f"User input for Screen 2: {user_data}")
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
                logger.info(f"Response: {response_data}")
                return JsonResponse(response_data)

            # Display summary and end session
            msg = f"You are {session['feeling']} {session['reason']}."
            response_data = {
                "USERID": ussd_id,
                "MSISDN": msisdn,
                "MSG": msg,
                "MSGTYPE": False  # End session
            }
            del sessions[session_id]  # End session
            logger.info(f"Response: {response_data}")
            return JsonResponse(response_data)


        # Logic 2: Direct Access (*920*1806*1#)
        elif len(parts) == 3:  # User dialed *920*1806*1#
            logger.info(f"User accessed direct Screen 1 with input: {parts[2]}")
            screen1_choice = parts[2]
            if screen1_choice == '1':
                session['feeling'] = 'Feeling fine'
            elif screen1_choice == '2':
                session['feeling'] = 'Feeling frisky'
            elif screen1_choice == '3':
                session['feeling'] = 'Not well'
            else:
                logger.error("Invalid choice in Screen 1 for direct access")
                return JsonResponse({'error': 'Invalid choice in Screen 1'}, status=400)
            # Move to Screen 2
            msg = f"Why are you {session['feeling']}?\n1. Money\n2. Relationship\n3. A lot"
            session['screen'] = 2
            response_data = {
                "USERID": ussd_id,
                "MSISDN": msisdn,
                "MSG": msg,
                "MSGTYPE": True
            }
            logger.info(f"Response: {response_data}")
            return JsonResponse(response_data)

        # Logic 3: Automatic Summary (*920*1806*1*1#)
        elif len(parts) == 4:  # User dialed *920*1806*1*1#
            logger.info(f"User accessed automatic summary with inputs: {parts[2]}, {parts[3]}")
            screen1_choice = parts[2]
            screen2_choice = parts[3]
            # Handle Screen 1 choice
            if screen1_choice == '1':
                session['feeling'] = 'Feeling fine'
            elif screen1_choice == '2':
                session['feeling'] = 'Feeling frisky'
            elif screen1_choice == '3':
                session['feeling'] = 'Not well'
            else:
                logger.error("Invalid choice in Screen 1 for automatic summary")
                return JsonResponse({'error': 'Invalid choice in Screen 1'}, status=400)
            # Handle Screen 2 choice
            if screen2_choice == '1':
                session['reason'] = 'because of money'
            elif screen2_choice == '2':
                session['reason'] = 'because of relationship'
            elif screen2_choice == '3':
                session['reason'] = 'because of a lot'
            else:
                logger.error("Invalid choice in Screen 2 for automatic summary")
                return JsonResponse({'error': 'Invalid choice in Screen 2'}, status=400)
            # Display summary
            msg = f"You are {session['feeling']} {session['reason']}."
            response_data = {
                "USERID": ussd_id,
                "MSISDN": msisdn,
                "MSG": msg,
                "MSGTYPE": False  # End session
            }
            del sessions[session_id]  # End session
            logger.info(f"Response: {response_data}")
            return JsonResponse(response_data)
        else:
            logger.error("Invalid USSD format")
            return JsonResponse({'error': 'Invalid USSD format'}, status=400)

    # If request method is not POST, return a 405 Method Not Allowed error
    logger.error("Method not allowed")
    return JsonResponse({'error': 'Method not allowed'}, status=405)

import datetime
import logging
import time
from typing import List, Optional
import azure.functions as func
from src.config import ConfigLoader
from src.service import GymBookingService
from src.models import AppConfig, UserConfig, ClassConfig, GymClass, LoginResult

app = func.FunctionApp()

# Trigger at 08:00:05 local time (Europe/Luxembourg).
# NOTE: Azure Functions uses the function app's timezone when WEBSITE_TIME_ZONE is set (Windows plan).
# Ensure the Function App has WEBSITE_TIME_ZONE=Europe/Luxembourg so the schedule runs at 08:00:05 Luxembourg time.
@app.timer_trigger(schedule="5 0 8 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def gym_booking_timer_trigger(myTimer: func.TimerRequest) -> None:
    # Use local time (assumed to be Europe/Luxembourg) for all booking logic
    local_timestamp = datetime.datetime.now().isoformat()

    logging.info('Gym booking script started at %s', local_timestamp)

    try:
        # 1. Load configuration and initialize service
        config = ConfigLoader().load()
        service = GymBookingService(config.app_id, config.client, config.client_version)

        # 2. Identify classes to book today
        # Use local time (Europe/Luxembourg) to match the gym's booking opening at 08:00 local
        now_local = datetime.datetime.now()
        current_weekday = now_local.strftime("%A")
        classes_to_book = [c for c in config.classes if c.weekday.lower() == current_weekday.lower()]

        if not classes_to_book:
            logging.info(f"No classes scheduled for booking today ({current_weekday}).")
            return

        # 3. Process each class and interested users
        for class_config in classes_to_book:
            _process_class_booking(service, config, class_config, now_local)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")

    logging.info('Gym booking script finished.')

def _process_class_booking(service: GymBookingService, config: AppConfig, class_config: ClassConfig, now_local: datetime.datetime):
    logging.info(f"Processing class: {class_config.name}")

    for username in class_config.user_names:
        user = next((u for u in config.users if u.username == username), None)
        if not user or not user.password or not user.username:
            logging.warning(f"User {username} not found in configuration or values are empty.")
            continue

        _book_for_user(service, user, class_config, now_local, config.facility_id)

def _book_for_user(service: GymBookingService, user: UserConfig, class_config: ClassConfig, now_local: datetime.datetime, facility_id: str):
    logging.info(f"Attempting booking for user: {user.username}")

    # Login
    login_result = service.login(user)
    if not login_result:
        return

    # Fetch classes for the next 7 days (use local dates)
    today_str = now_local.strftime("%Y-%m-%d")
    to_date_str = (now_local + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    available_classes = service.fetch_classes(login_result.token, facility_id, today_str, to_date_str)

    # Find the specific class instance where booking opens today
    target_class = _find_target_class(available_classes, class_config.name, today_str)

    if target_class:
        _execute_booking(service, login_result, target_class, class_config, user)
    else:
        logging.warning(f"Could not find a class instance for {class_config.name} opening today for {user.username}.")

def _find_target_class(available_classes: List[GymClass], class_name: str, today_str: str) -> Optional[GymClass]:
    for ac in available_classes:
        if ac.name.upper() == class_name.upper():
            # booking_opens_on is typically in ISO format like 2026-03-31T07:00:00Z
            opening_date = ac.booking_opens_on.split('T')[0]
            if opening_date == today_str:
                return ac
    return None

def _execute_booking(service: GymBookingService, login_result: LoginResult, target_class: GymClass, class_config: ClassConfig, user: UserConfig):
    logging.info(f"Found target class: {target_class.name} (ID: {target_class.id})")

    # Precision wait: if booking opens in the next few minutes, wait for it
    _wait_for_opening(target_class.booking_opens_on)

    booking_res = service.book_class(
        login_result.token,
        login_result.user_id,
        target_class.id,
        target_class.partition_date
    )

    if booking_res.result == "Booked":
        logging.info(f"Successfully booked {class_config.name} for {user.username}")
    elif booking_res.result == "UserAlreadyBooked":
        logging.info(f"{user.username} is already booked for {class_config.name}")
    else:
        logging.error(f"Failed to book for {user.username}: {booking_res.result} - {booking_res.error_message}")

def _wait_for_opening(booking_opens_on: str):
    if not booking_opens_on:
        return

    try:
        # Normalize ISO format for Python 3.7+ (handle 'Z' or '+00:00')
        iso_str = booking_opens_on.replace('Z', '+00:00')
        opening_time = datetime.datetime.fromisoformat(iso_str)

        # If opening_time is timezone-aware (e.g., with +00:00), convert to local naive datetime
        if opening_time.tzinfo is not None:
            opening_time = datetime.datetime.fromtimestamp(opening_time.timestamp())

        while True:
            now_local = datetime.datetime.now()
            wait_seconds = (opening_time - now_local).total_seconds()

            if wait_seconds <= 0:
                break

            if wait_seconds > 600: # Don't wait more than 10 minutes to avoid function timeout
                logging.warning(f"Booking opens in {wait_seconds} seconds. This is too long to wait. Attempting anyway...")
                break

            logging.info(f"Waiting for booking to open in {wait_seconds:.2f} seconds...")
            # Sleep in small increments to be precise
            sleep_time = min(wait_seconds, 1.0)
            time.sleep(sleep_time)
    except Exception as e:
        logging.error(f"Error in wait_for_opening: {e}")
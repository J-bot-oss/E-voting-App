# Main controller for the E-Voting System.
# This file connects the UI, services, storage, and shared utilities.

import storage.state as state
from storage.store import load_data, save_data

from services.authentication_service import login_admin, login_voter, logout, register_voter
from services.admin_service import create_admin, get_all_admins, deactivate_admin
from services.candidate_service import (
    create_candidate,
    get_all_candidates,
    update_candidate,
    delete_candidate,
    search_candidates,
)
from services.poll_service import (
    create_position,
    get_all_positions,
    update_position,
    delete_position,
    create_poll,
    get_all_polls,
    get_open_polls,
    get_closed_polls,
    update_poll,
    delete_poll,
    open_close_poll,
    assign_candidates_to_poll,
    create_station,
    get_all_stations,
    update_station,
    delete_station,
)
from services.voter_service import (
    get_all_voters,
    get_unverified_voters,
    verify_voter,
    verify_all_voters,
    deactivate_voter,
    search_voters,
    change_voter_password,
)
from services.voting_service import (
    get_available_polls_for_voter,
    cast_vote,
    get_voting_history,
)
from services.result_service import (
    get_poll_results,
    get_station_wise_results,
    get_detailed_statistics,
    get_audit_log,
    filter_audit_log,
)

from ui.Menus import (
    show_login_menu,
    show_admin_login_screen,
    show_voter_login_screen,
    show_voter_registration_form,
    show_voter_registration_success,
    show_admin_dashboard,
    show_voter_dashboard,
    show_candidates_table,
    show_candidate_search_menu,
    show_stations_table,
    show_all_polls,
    show_voters_table,
    show_voter_profile,
    show_results_bar_chart,
    show_admins_table,
    show_audit_log_menu,
    show_audit_entries,
)

from ui.Display import (
    display_error,
    display_success,
    display_warning,
    display_info_message,
    menu_item,
    status_badge,
)

from utils.display import (
    header,
    subheader,
    table_header,
    table_divider,
    prompt,
    clear_screen,
    pause,
)
from utils.helpers import hash_password, current_timestamp, masked_input
from utils.colors import (
    THEME_ADMIN,
    THEME_ADMIN_ACCENT,
    THEME_VOTER,
    THEME_VOTER_ACCENT,
    THEME_LOGIN,
    BOLD,
    DIM,
    GREEN,
    RED,
    YELLOW,
    GRAY,
    BRIGHT_BLUE,
    BRIGHT_GREEN,
    BRIGHT_YELLOW,
    BRIGHT_CYAN,
    RESET,
)
from utils.constants import (
    REQUIRED_EDUCATION_LEVELS,
    VALID_POSITION_LEVELS,
    VALID_ELECTION_TYPES,
    ADMIN_ROLES,
)


# ---------------------------------------------------
# Helper functions
# ---------------------------------------------------

def ensure_default_admin():
    """Create the default admin if none exists."""
    if state.admins:
        return

    state.admins[1] = {
        "id": 1,
        "username": "admin",
        "password": hash_password("admin123"),
        "full_name": "System Administrator",
        "email": "admin@evote.com",
        "role": "super_admin",
        "created_at": current_timestamp(),
        "is_active": True,
    }
    state.admin_id_counter = 2
    save_data()


def prompt_int(message: str, allow_empty: bool = False):
    """Read an integer safely from the user."""
    value = prompt(message)
    if allow_empty and value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def prompt_list_of_ints(message: str):
    """Read comma-separated integers from the user."""
    value = prompt(message)
    if not value:
        return []
    try:
        return [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError:
        return None


def show_positions_table(positions):
    clear_screen()
    header("ALL POSITIONS", THEME_ADMIN)

    if not positions:
        print()
        display_info_message("No positions found.")
        pause()
        return

    print()
    table_header(
        f"{'ID':<5} {'Title':<25} {'Level':<12} {'Seats':<8} {'Min Age':<10} {'Status':<10}",
        THEME_ADMIN,
    )
    table_divider(75, THEME_ADMIN)

    for position in positions.values():
        status = status_badge("Active", True) if position["is_active"] else status_badge("Inactive", False)
        print(
            f"  {position['id']:<5} {position['title']:<25} {position['level']:<12} "
            f"{position['max_winners']:<8} {position['min_candidate_age']:<10} {status}"
        )

    print(f"\n  {DIM}Total Positions: {len(positions)}{RESET}")
    pause()


def show_open_polls_for_voter(voter):
    clear_screen()
    header("OPEN POLLS", THEME_VOTER)

    available_polls = get_available_polls_for_voter(voter)

    if not available_polls:
        print()
        display_info_message("No available polls to vote in.")
        pause()
        return

    for poll_id, poll in available_polls.items():
        print(f"\n  {BOLD}{THEME_VOTER}Poll #{poll_id}: {poll['title']}{RESET}")
        print(
            f"  {DIM}Type:{RESET} {poll['election_type']}  "
            f"{DIM}│  Period:{RESET} {poll['start_date']} to {poll['end_date']}"
        )
        for position in poll["positions"]:
            print(f"    {THEME_VOTER_ACCENT}▸{RESET} {position['position_title']}")
            for candidate_id in position["candidate_ids"]:
                candidate = state.candidates.get(candidate_id)
                if candidate:
                    print(
                        f"      • {candidate['full_name']} "
                        f"{DIM}({candidate['party']}) | Age: {candidate['age']} | Edu: {candidate['education']}{RESET}"
                    )

    pause()


def show_voting_history_screen(voter):
    clear_screen()
    header("MY VOTING HISTORY", THEME_VOTER)

    history = get_voting_history(voter)

    if not history:
        print()
        display_info_message("You have not voted in any polls yet.")
        pause()
        return

    for item in history:
        print(f"\n  {BOLD}{THEME_VOTER}Poll #{item['poll_id']}: {item['poll_title']}{RESET}")
        print(
            f"  {DIM}Type:{RESET} {item['election_type']}  "
            f"{DIM}│  Status:{RESET} {item['poll_status'].upper()}"
        )

        for vote in item["votes"]:
            if vote["abstained"]:
                print(f"    {THEME_VOTER_ACCENT}▸{RESET} Position {vote['position_id']}: {GRAY}ABSTAINED{RESET}")
            else:
                candidate_name = state.candidates.get(vote["candidate_id"], {}).get("full_name", "Unknown")
                print(f"    {THEME_VOTER_ACCENT}▸{RESET} Position {vote['position_id']}: {BRIGHT_GREEN}{candidate_name}{RESET}")

    pause()


def show_closed_results_for_voter():
    clear_screen()
    header("ELECTION RESULTS", THEME_VOTER)

    closed_polls = get_closed_polls()
    if not closed_polls:
        print()
        display_info_message("No closed polls with results.")
        pause()
        return

    for poll in closed_polls.values():
        print(f"\n  {BOLD}{THEME_VOTER}{poll['title']}{RESET}")
        print(f"  {DIM}Type:{RESET} {poll['election_type']}  {DIM}│  Votes:{RESET} {poll['total_votes_cast']}")
        show_results_bar_chart(
            poll,
            state.votes,
            state.candidates,
            state.positions,
            state.voters,
            THEME_VOTER,
            winner_label="WINNER",
        )

    pause()


def collect_candidate_form(current_user):
    clear_screen()
    header("CREATE NEW CANDIDATE", THEME_ADMIN)
    print()

    full_name = prompt("Full Name: ")
    national_id = prompt("National ID: ")
    dob_str = prompt("Date of Birth (YYYY-MM-DD): ")
    gender = prompt("Gender (M/F/Other): ").upper()

    subheader("Education Levels", THEME_ADMIN_ACCENT)
    for index, level in enumerate(REQUIRED_EDUCATION_LEVELS, start=1):
        print(f"    {THEME_ADMIN}{index}.{RESET} {level}")

    education_choice = prompt_int("Select education level: ")
    if education_choice is None or education_choice < 1 or education_choice > len(REQUIRED_EDUCATION_LEVELS):
        display_error("Invalid education choice.")
        pause()
        return None

    education = REQUIRED_EDUCATION_LEVELS[education_choice - 1]
    party = prompt("Political Party/Affiliation: ")
    manifesto = prompt("Brief Manifesto/Bio: ")
    address = prompt("Address: ")
    phone = prompt("Phone: ")
    email = prompt("Email: ")
    criminal_record = prompt("Has Criminal Record? (yes/no): ").lower()
    years_experience = prompt_int("Years of Public Service/Political Experience: ")
    if years_experience is None:
        years_experience = 0

    return {
        "full_name": full_name,
        "national_id": national_id,
        "dob_str": dob_str,
        "gender": gender,
        "education": education,
        "party": party,
        "manifesto": manifesto,
        "address": address,
        "phone": phone,
        "email": email,
        "criminal_record": criminal_record,
        "years_experience": years_experience,
        "created_by": current_user["username"],
    }


def collect_station_form(current_user):
    clear_screen()
    header("CREATE VOTING STATION", THEME_ADMIN)
    print()

    name = prompt("Station Name: ")
    location = prompt("Location/Address: ")
    region = prompt("Region/District: ")
    capacity = prompt_int("Voter Capacity: ")
    supervisor = prompt("Station Supervisor Name: ")
    contact = prompt("Contact Phone: ")
    opening_time = prompt("Opening Time (e.g. 08:00): ")
    closing_time = prompt("Closing Time (e.g. 17:00): ")

    if capacity is None:
        display_error("Invalid capacity.")
        pause()
        return None

    return {
        "name": name,
        "location": location,
        "region": region,
        "capacity": capacity,
        "supervisor": supervisor,
        "contact": contact,
        "opening_time": opening_time,
        "closing_time": closing_time,
        "created_by": current_user["username"],
    }


def collect_position_form(current_user):
    clear_screen()
    header("CREATE POSITION", THEME_ADMIN)
    print()

    title = prompt("Position Title: ")
    description = prompt("Description: ")
    level = prompt("Level (National/Regional/Local): ")
    max_winners = prompt_int("Number of winners/seats: ")
    min_candidate_age = prompt_int("Minimum candidate age (press Enter for default 25): ", allow_empty=True)

    if max_winners is None:
        display_error("Invalid number of winners.")
        pause()
        return None

    return {
        "title": title,
        "description": description,
        "level": level,
        "max_winners": max_winners,
        "min_candidate_age": min_candidate_age,
        "created_by": current_user["username"],
    }


def collect_poll_form(current_user):
    positions = get_all_positions()
    stations = get_all_stations()

    if not positions:
        display_error("No positions available. Create positions first.")
        pause()
        return None

    if not stations:
        display_error("No voting stations available. Create stations first.")
        pause()
        return None

    clear_screen()
    header("CREATE POLL / ELECTION", THEME_ADMIN)
    print()

    title = prompt("Poll/Election Title: ")
    description = prompt("Description: ")
    election_type = prompt("Election Type (General/Primary/By-election/Referendum): ")
    start_date = prompt("Start Date (YYYY-MM-DD): ")
    end_date = prompt("End Date (YYYY-MM-DD): ")

    subheader("Available Positions", THEME_ADMIN_ACCENT)
    for position in positions.values():
        if position["is_active"]:
            print(
                f"    {THEME_ADMIN}{position['id']}.{RESET} {position['title']} "
                f"{DIM}({position['level']}) - {position['max_winners']} seat(s){RESET}"
            )

    selected_position_ids = prompt_list_of_ints("Enter Position IDs (comma-separated): ")
    if selected_position_ids is None:
        display_error("Invalid position selection.")
        pause()
        return None

    subheader("Available Voting Stations", THEME_ADMIN_ACCENT)
    for station in stations.values():
        if station["is_active"]:
            print(
                f"    {THEME_ADMIN}{station['id']}.{RESET} {station['name']} "
                f"{DIM}({station['location']}){RESET}"
            )

    use_all = prompt("Use all active stations? (yes/no): ").lower()
    if use_all == "yes":
        selected_station_ids = [station_id for station_id, station in stations.items() if station["is_active"]]
    else:
        selected_station_ids = prompt_list_of_ints("Enter Station IDs (comma-separated): ")
        if selected_station_ids is None:
            display_error("Invalid station selection.")
            pause()
            return None

    return {
        "title": title,
        "description": description,
        "election_type": election_type,
        "start_date": start_date,
        "end_date": end_date,
        "selected_position_ids": selected_position_ids,
        "selected_station_ids": selected_station_ids,
        "created_by": current_user["username"],
    }


def collect_admin_form():
    clear_screen()
    header("CREATE ADMIN ACCOUNT", THEME_ADMIN)
    print()

    username = prompt("Username: ")
    full_name = prompt("Full Name: ")
    email = prompt("Email: ")
    password = masked_input("Password: ").strip()

    subheader("Available Roles", THEME_ADMIN_ACCENT)
    for key, role in ADMIN_ROLES.items():
        print(f"    {THEME_ADMIN}{key}.{RESET} {role}")

    role_choice = prompt("Select role (1-4): ")
    role = ADMIN_ROLES.get(role_choice)

    return {
        "username": username,
        "full_name": full_name,
        "email": email,
        "password": password,
        "role": role,
    }


def create_candidate_flow(current_user):
    form_data = collect_candidate_form(current_user)
    if not form_data:
        return

    success, message = create_candidate(form_data)
    if success:
        display_success(message)
    else:
        display_error(message)
    pause()


def update_candidate_flow(current_user):
    candidates = get_all_candidates()
    show_candidates_table(candidates)

    candidate_id = prompt_int("Enter Candidate ID to update: ")
    if candidate_id is None:
        display_error("Invalid input.")
        pause()
        return

    updates = {
        "full_name": prompt("Full Name (press Enter to keep current): "),
        "party": prompt("Party (press Enter to keep current): "),
        "manifesto": prompt("Manifesto (press Enter to keep current): "),
        "phone": prompt("Phone (press Enter to keep current): "),
        "email": prompt("Email (press Enter to keep current): "),
        "address": prompt("Address (press Enter to keep current): "),
        "years_experience": prompt("Years Experience (press Enter to keep current): "),
    }

    result, message = update_candidate(candidate_id, updates, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def delete_candidate_flow(current_user):
    candidates = get_all_candidates()
    show_candidates_table(candidates)

    candidate_id = prompt_int("Enter Candidate ID to deactivate: ")
    if candidate_id is None:
        display_error("Invalid input.")
        pause()
        return

    result, message = delete_candidate(candidate_id, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def search_candidates_flow():
    choice = show_candidate_search_menu()

    if choice == "1":
        results = search_candidates("name", prompt("Enter name to search: "))
    elif choice == "2":
        results = search_candidates("party", prompt("Enter party name: "))
    elif choice == "3":
        for index, level in enumerate(REQUIRED_EDUCATION_LEVELS, start=1):
            print(f"    {index}. {level}")
        education_choice = prompt_int("Select education level: ")
        if education_choice is None or education_choice < 1 or education_choice > len(REQUIRED_EDUCATION_LEVELS):
            display_error("Invalid choice.")
            pause()
            return
        results = search_candidates("education", REQUIRED_EDUCATION_LEVELS[education_choice - 1])
    elif choice == "4":
        min_age = prompt_int("Min age: ")
        max_age = prompt_int("Max age: ")
        if min_age is None or max_age is None:
            display_error("Invalid age range.")
            pause()
            return
        results = search_candidates("age_range", (min_age, max_age))
    else:
        display_error("Invalid choice.")
        pause()
        return

    show_candidates_table({candidate["id"]: candidate for candidate in results})


def create_station_flow(current_user):
    form_data = collect_station_form(current_user)
    if not form_data:
        return

    success, message = create_station(form_data)
    if success:
        display_success(message)
    else:
        display_error(message)
    pause()


def update_station_flow(current_user):
    stations = get_all_stations()
    show_stations_table(stations, get_all_voters())

    station_id = prompt_int("Enter Station ID to update: ")
    if station_id is None:
        display_error("Invalid input.")
        pause()
        return

    updates = {
        "name": prompt("Name (press Enter to keep current): "),
        "location": prompt("Location (press Enter to keep current): "),
        "region": prompt("Region (press Enter to keep current): "),
        "capacity": prompt("Capacity (press Enter to keep current): "),
        "supervisor": prompt("Supervisor (press Enter to keep current): "),
        "contact": prompt("Contact (press Enter to keep current): "),
    }

    if updates["capacity"]:
        try:
            updates["capacity"] = int(updates["capacity"])
        except ValueError:
            display_error("Invalid capacity.")
            pause()
            return

    result, message = update_station(station_id, updates, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def delete_station_flow(current_user):
    stations = get_all_stations()
    show_stations_table(stations, get_all_voters())

    station_id = prompt_int("Enter Station ID to deactivate: ")
    if station_id is None:
        display_error("Invalid input.")
        pause()
        return

    result, message = delete_station(station_id, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def create_position_flow(current_user):
    form_data = collect_position_form(current_user)
    if not form_data:
        return

    success, message = create_position(form_data)
    if success:
        display_success(message)
    else:
        display_error(message)
    pause()


def update_position_flow(current_user):
    positions = get_all_positions()
    show_positions_table(positions)

    position_id = prompt_int("Enter Position ID to update: ")
    if position_id is None:
        display_error("Invalid input.")
        pause()
        return

    updates = {
        "title": prompt("Title (press Enter to keep current): "),
        "description": prompt("Description (press Enter to keep current): "),
        "level": prompt("Level (press Enter to keep current): "),
        "max_winners": prompt("Seats (press Enter to keep current): "),
    }

    if updates["max_winners"]:
        try:
            updates["max_winners"] = int(updates["max_winners"])
        except ValueError:
            display_error("Invalid seats value.")
            pause()
            return

    result, message = update_position(position_id, updates, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def delete_position_flow(current_user):
    positions = get_all_positions()
    show_positions_table(positions)

    position_id = prompt_int("Enter Position ID to deactivate: ")
    if position_id is None:
        display_error("Invalid input.")
        pause()
        return

    result, message = delete_position(position_id, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def create_poll_flow(current_user):
    form_data = collect_poll_form(current_user)
    if not form_data:
        return

    success, message = create_poll(form_data)
    if success:
        display_success(message)
    else:
        display_error(message)
    pause()


def update_poll_flow(current_user):
    show_all_polls(get_all_polls(), get_all_candidates())

    poll_id = prompt_int("Enter Poll ID to update: ")
    if poll_id is None:
        display_error("Invalid input.")
        pause()
        return

    updates = {
        "title": prompt("Title (press Enter to keep current): "),
        "description": prompt("Description (press Enter to keep current): "),
        "election_type": prompt("Election Type (press Enter to keep current): "),
        "start_date": prompt("Start Date YYYY-MM-DD (press Enter to keep current): "),
        "end_date": prompt("End Date YYYY-MM-DD (press Enter to keep current): "),
    }

    result, message = update_poll(poll_id, updates, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def delete_poll_flow(current_user):
    show_all_polls(get_all_polls(), get_all_candidates())

    poll_id = prompt_int("Enter Poll ID to delete: ")
    if poll_id is None:
        display_error("Invalid input.")
        pause()
        return

    result, message = delete_poll(poll_id, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def open_close_poll_flow(current_user):
    show_all_polls(get_all_polls(), get_all_candidates())

    poll_id = prompt_int("Enter Poll ID: ")
    if poll_id is None:
        display_error("Invalid input.")
        pause()
        return

    result, message, _ = open_close_poll(poll_id, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def assign_candidates_to_poll_flow(current_user):
    polls = get_all_polls()
    candidates = get_all_candidates()

    show_all_polls(polls, candidates)

    poll_id = prompt_int("Enter Poll ID: ")
    if poll_id is None or poll_id not in polls:
        display_error("Invalid poll.")
        pause()
        return

    poll = polls[poll_id]

    if poll["status"] == "open":
        display_error("Cannot modify candidates of an open poll.")
        pause()
        return

    print()
    subheader("Positions in Poll", THEME_ADMIN_ACCENT)
    for index, position in enumerate(poll["positions"], start=1):
        print(f"    {index}. {position['position_title']}")

    position_choice = prompt_int("Select position number: ")
    if position_choice is None or position_choice < 1 or position_choice > len(poll["positions"]):
        display_error("Invalid position selection.")
        pause()
        return

    subheader("Available Candidates", THEME_ADMIN_ACCENT)
    for candidate in candidates.values():
        if candidate["is_active"] and candidate["is_approved"]:
            print(
                f"    {candidate['id']}. {candidate['full_name']} "
                f"{DIM}({candidate['party']}){RESET}"
            )

    candidate_ids = prompt_list_of_ints("Enter Candidate IDs (comma-separated): ")
    if candidate_ids is None:
        display_error("Invalid candidate list.")
        pause()
        return

    result, message = assign_candidates_to_poll(
        poll_id,
        position_choice - 1,
        candidate_ids,
        current_user["username"],
    )
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def verify_voter_flow(current_user):
    clear_screen()
    header("VERIFY VOTER", THEME_ADMIN)
    unverified = get_unverified_voters()

    if not unverified:
        print()
        display_info_message("No unverified voters.")
        pause()
        return

    subheader("Unverified Voters", THEME_ADMIN_ACCENT)
    for voter in unverified.values():
        print(
            f"  {THEME_ADMIN}{voter['id']}.{RESET} {voter['full_name']} "
            f"{DIM}│ NID: {voter['national_id']} │ Card: {voter['voter_card_number']}{RESET}"
        )

    print()
    menu_item(1, "Verify a single voter", THEME_ADMIN)
    menu_item(2, "Verify all pending voters", THEME_ADMIN)
    choice = prompt("\nChoice: ")

    if choice == "1":
        voter_id = prompt_int("Enter Voter ID: ")
        if voter_id is None:
            display_error("Invalid input.")
            pause()
            return
        result, message = verify_voter(voter_id, current_user["username"])
    elif choice == "2":
        result, message = verify_all_voters(current_user["username"])
    else:
        display_error("Invalid choice.")
        pause()
        return

    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def deactivate_voter_flow(current_user):
    show_voters_table(get_all_voters())

    voter_id = prompt_int("Enter Voter ID to deactivate: ")
    if voter_id is None:
        display_error("Invalid input.")
        pause()
        return

    result, message = deactivate_voter(voter_id, current_user["username"])
    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def search_voters_flow():
    clear_screen()
    header("SEARCH VOTERS", THEME_ADMIN)
    subheader("Search by", THEME_ADMIN_ACCENT)
    menu_item(1, "Name", THEME_ADMIN)
    menu_item(2, "Voter Card Number", THEME_ADMIN)
    menu_item(3, "National ID", THEME_ADMIN)
    menu_item(4, "Station", THEME_ADMIN)
    choice = prompt("\nChoice: ")

    if choice == "1":
        results = search_voters("name", prompt("Name: "))
    elif choice == "2":
        results = search_voters("card", prompt("Card Number: "))
    elif choice == "3":
        results = search_voters("national_id", prompt("National ID: "))
    elif choice == "4":
        station_id = prompt_int("Station ID: ")
        if station_id is None:
            display_error("Invalid input.")
            pause()
            return
        results = search_voters("station", station_id)
    else:
        display_error("Invalid choice.")
        pause()
        return

    show_voters_table({voter["id"]: voter for voter in results})


def create_admin_flow(current_user):
    form_data = collect_admin_form()
    if not form_data or not form_data["role"]:
        display_error("Invalid role selected.")
        pause()
        return

    success, message = create_admin(form_data, current_user["username"])
    if success:
        display_success(message)
    else:
        display_error(message)
    pause()


def deactivate_admin_flow(current_user):
    show_admins_table(get_all_admins())

    admin_id = prompt_int("Enter Admin ID to deactivate: ")
    if admin_id is None:
        display_error("Invalid input.")
        pause()
        return

    result, message = deactivate_admin(
        admin_id,
        current_user["id"],
        current_user["username"],
    )

    if result:
        display_success(message)
    else:
        display_error(message)
    pause()


def show_poll_results_flow():
    show_all_polls(get_all_polls(), get_all_candidates())

    poll_id = prompt_int("Enter Poll ID: ")
    if poll_id is None:
        display_error("Invalid input.")
        pause()
        return

    result = get_poll_results(poll_id)
    if not result:
        display_error("Poll not found.")
        pause()
        return

    clear_screen()
    header(f"RESULTS: {result['poll']['title']}", THEME_ADMIN)
    print(
        f"  {DIM}Eligible:{RESET} {result['total_eligible']}  "
        f"{DIM}│  Turnout:{RESET} {result['turnout']:.1f}%"
    )
    show_results_bar_chart(
        result["poll"],
        state.votes,
        state.candidates,
        state.positions,
        state.voters,
        THEME_ADMIN,
        winner_label="★ WINNER",
    )
    pause()


def show_detailed_statistics_flow():
    stats = get_detailed_statistics()

    clear_screen()
    header("DETAILED STATISTICS", THEME_ADMIN)

    subheader("SYSTEM OVERVIEW", THEME_ADMIN_ACCENT)
    print(f"  Candidates: {stats['candidates']['total']} (Active: {stats['candidates']['active']})")
    print(f"  Voters: {stats['voters']['total']} (Verified: {stats['voters']['verified']}, Active: {stats['voters']['active']})")
    print(f"  Stations: {stats['stations']['total']} (Active: {stats['stations']['active']})")
    print(
        f"  Polls: {stats['polls']['total']} "
        f"(Open: {stats['polls']['open']}, Closed: {stats['polls']['closed']}, Draft: {stats['polls']['draft']})"
    )
    print(f"  Total Votes: {stats['total_votes']}")

    subheader("VOTER DEMOGRAPHICS", THEME_ADMIN_ACCENT)
    for gender, count in stats["gender_counts"].items():
        print(f"  {gender}: {count}")

    print(f"\n  {BOLD}Age Distribution:{RESET}")
    for group, count in stats["age_groups"].items():
        print(f"  {group}: {count}")

    subheader("STATION LOAD", THEME_ADMIN_ACCENT)
    for station in stats["station_loads"]:
        print(
            f"  {station['name']}: {station['voter_count']}/{station['capacity']} "
            f"({station['load_percent']:.1f}%)"
        )

    subheader("PARTY DISTRIBUTION", THEME_ADMIN_ACCENT)
    for party, count in stats["party_counts"].items():
        print(f"  {party}: {count}")

    subheader("EDUCATION LEVELS", THEME_ADMIN_ACCENT)
    for education, count in stats["education_counts"].items():
        print(f"  {education}: {count}")

    pause()


def show_station_wise_results_flow():
    show_all_polls(get_all_polls(), get_all_candidates())

    poll_id = prompt_int("Enter Poll ID: ")
    if poll_id is None:
        display_error("Invalid input.")
        pause()
        return

    result = get_station_wise_results(poll_id)
    if not result:
        display_error("Poll not found.")
        pause()
        return

    clear_screen()
    header(f"STATION RESULTS: {result['poll']['title']}", THEME_ADMIN)

    for station_result in result["station_results"]:
        station = station_result["station"]
        subheader(f"{station['name']} ({station['location']})", BRIGHT_CYAN)
        print(
            f"  Registered: {station_result['registered_at_station']}  "
            f"│  Voted: {station_result['voters_who_voted']}  "
            f"│  Turnout: {station_result['station_turnout']:.1f}%"
        )

        for breakdown in station_result["position_breakdowns"]:
            print(f"    ▸ {breakdown['position_title']}")
            for candidate_id, count in breakdown["vote_counts"].items():
                candidate_name = state.candidates.get(candidate_id, {}).get("full_name", "?")
                print(f"      {candidate_name}: {count}")
            if breakdown["abstain_count"] > 0:
                print(f"      Abstained: {breakdown['abstain_count']}")

    pause()


def show_audit_log_flow():
    entries = get_audit_log()
    choice = show_audit_log_menu()

    if choice == "1":
        entries = entries[-20:]
    elif choice == "2":
        entries = entries
    elif choice == "3":
        filter_term = prompt("Enter action type: ")
        entries = filter_audit_log("action", filter_term)
    elif choice == "4":
        filter_term = prompt("Enter username/card number: ")
        entries = filter_audit_log("user", filter_term)
    else:
        display_error("Invalid choice.")
        pause()
        return

    clear_screen()
    header("AUDIT LOG", THEME_ADMIN)
    show_audit_entries(entries)
    pause()


def cast_vote_flow(voter):
    available_polls = get_available_polls_for_voter(voter)

    if not available_polls:
        display_info_message("No available polls to vote in.")
        pause()
        return

    clear_screen()
    header("CAST YOUR VOTE", THEME_VOTER)
    subheader("Available Polls", THEME_VOTER_ACCENT)

    for poll_id, poll in available_polls.items():
        print(f"  {THEME_VOTER}{poll_id}.{RESET} {poll['title']} {DIM}({poll['election_type']}){RESET}")

    poll_id = prompt_int("\nSelect Poll ID to vote: ")
    if poll_id is None or poll_id not in available_polls:
        display_error("Invalid poll selection.")
        pause()
        return

    poll = available_polls[poll_id]
    vote_selections = []

    clear_screen()
    header(f"Voting: {poll['title']}", THEME_VOTER)
    display_info_message("Please select ONE candidate for each position.\n")

    for position in poll["positions"]:
        subheader(position["position_title"], THEME_VOTER_ACCENT)

        if not position["candidate_ids"]:
            display_info_message("No candidates for this position.")
            continue

        for index, candidate_id in enumerate(position["candidate_ids"], start=1):
            candidate = state.candidates.get(candidate_id)
            if candidate:
                print(f"    {THEME_VOTER}{BOLD}{index}.{RESET} {candidate['full_name']} {DIM}({candidate['party']}){RESET}")
                print(
                    f"       {DIM}Age: {candidate['age']} │ Edu: {candidate['education']} "
                    f"│ Exp: {candidate['years_experience']} yrs{RESET}"
                )
                if candidate["manifesto"]:
                    print(f"       {DIM}{candidate['manifesto'][:80]}...{RESET}")

        print(f"    {GRAY}{BOLD}0.{RESET} {GRAY}Abstain / Skip{RESET}")
        vote_choice = prompt_int(f"\nYour choice for {position['position_title']}: ")

        if vote_choice is None or vote_choice == 0:
            vote_selections.append(
                {
                    "position_id": position["position_id"],
                    "abstained": True,
                }
            )
        elif 1 <= vote_choice <= len(position["candidate_ids"]):
            selected_candidate_id = position["candidate_ids"][vote_choice - 1]
            vote_selections.append(
                {
                    "position_id": position["position_id"],
                    "candidate_id": selected_candidate_id,
                    "abstained": False,
                }
            )
        else:
            vote_selections.append(
                {
                    "position_id": position["position_id"],
                    "abstained": True,
                }
            )

    print()
    confirm = prompt("Confirm your votes? This cannot be undone. (yes/no): ").lower()
    if confirm != "yes":
        display_info_message("Vote cancelled.")
        pause()
        return

    success, message, vote_hash = cast_vote(voter, poll_id, vote_selections)
    if success:
        display_success(message)
        print(f"  {DIM}Vote Reference:{RESET} {BRIGHT_YELLOW}{vote_hash}{RESET}")
    else:
        display_error(message)

    pause()


# ---------------------------------------------------
# Admin dashboard controller
# ---------------------------------------------------

def admin_loop(admin):
    while True:
        choice = show_admin_dashboard(admin)

        if choice == "1":
            create_candidate_flow(admin)
        elif choice == "2":
            show_candidates_table(get_all_candidates())
        elif choice == "3":
            update_candidate_flow(admin)
        elif choice == "4":
            delete_candidate_flow(admin)
        elif choice == "5":
            search_candidates_flow()

        elif choice == "6":
            create_station_flow(admin)
        elif choice == "7":
            show_stations_table(get_all_stations(), get_all_voters())
        elif choice == "8":
            update_station_flow(admin)
        elif choice == "9":
            delete_station_flow(admin)

        elif choice == "10":
            create_position_flow(admin)
        elif choice == "11":
            show_positions_table(get_all_positions())
        elif choice == "12":
            update_position_flow(admin)
        elif choice == "13":
            delete_position_flow(admin)
        elif choice == "14":
            create_poll_flow(admin)
        elif choice == "15":
            show_all_polls(get_all_polls(), get_all_candidates())
        elif choice == "16":
            update_poll_flow(admin)
        elif choice == "17":
            delete_poll_flow(admin)
        elif choice == "18":
            open_close_poll_flow(admin)
        elif choice == "19":
            assign_candidates_to_poll_flow(admin)

        elif choice == "20":
            show_voters_table(get_all_voters())
        elif choice == "21":
            verify_voter_flow(admin)
        elif choice == "22":
            deactivate_voter_flow(admin)
        elif choice == "23":
            search_voters_flow()

        elif choice == "24":
            create_admin_flow(admin)
        elif choice == "25":
            show_admins_table(get_all_admins())
        elif choice == "26":
            deactivate_admin_flow(admin)

        elif choice == "27":
            show_poll_results_flow()
        elif choice == "28":
            show_detailed_statistics_flow()
        elif choice == "29":
            show_audit_log_flow()
        elif choice == "30":
            show_station_wise_results_flow()

        elif choice == "31":
            save_data()
            display_success("Data saved successfully.")
            pause()

        elif choice == "32":
            logout()
            display_info_message("Logged out successfully.")
            pause()
            break

        else:
            display_error("Invalid choice.")
            pause()


# ---------------------------------------------------
# Voter dashboard controller
# ---------------------------------------------------

def voter_loop(voter):
    while True:
        station_name = state.voting_stations.get(voter["station_id"], {}).get("name", "Unknown")
        choice = show_voter_dashboard(voter, station_name)

        if choice == "1":
            show_open_polls_for_voter(voter)
        elif choice == "2":
            cast_vote_flow(voter)
        elif choice == "3":
            show_voting_history_screen(voter)
        elif choice == "4":
            show_closed_results_for_voter()
        elif choice == "5":
            show_voter_profile(voter, state.voting_stations)
        elif choice == "6":
            old_password = masked_input("Current Password: ").strip()
            new_password = masked_input("New Password: ").strip()
            confirm_password = masked_input("Confirm New Password: ").strip()

            if new_password != confirm_password:
                display_error("Passwords do not match.")
                pause()
                continue

            success, message = change_voter_password(voter["id"], old_password, new_password)
            if success:
                display_success(message)
            else:
                display_error(message)
            pause()

        elif choice == "7":
            logout()
            display_info_message("Logged out successfully.")
            pause()
            break

        else:
            display_error("Invalid choice.")
            pause()


# ---------------------------------------------------
# Main program loop
# ---------------------------------------------------

def main():
    load_data()
    ensure_default_admin()

    while True:
        choice = show_login_menu()

        if choice == "1":
            username, password = show_admin_login_screen()
            admin, status = login_admin(username, password)

            if status == "success":
                display_success(f"Welcome, {admin['full_name']}!")
                pause()
                admin_loop(admin)
            elif status == "deactivated":
                display_error("This account has been deactivated.")
                pause()
            else:
                display_error("Invalid credentials.")
                pause()

        elif choice == "2":
            voter_card, password = show_voter_login_screen()
            voter, status = login_voter(voter_card, password)

            if status == "success":
                display_success(f"Welcome, {voter['full_name']}!")
                pause()
                voter_loop(voter)
            elif status == "deactivated":
                display_error("This voter account has been deactivated.")
                pause()
            elif status == "unverified":
                display_warning("Your voter registration has not been verified yet.")
                pause()
            else:
                display_error("Invalid voter card number or password.")
                pause()

        elif choice == "3":
            form_data = show_voter_registration_form(state.voting_stations)

            if form_data:
                success, message, voter_card = register_voter(form_data)
                if success:
                    show_voter_registration_success(voter_card)
                else:
                    display_error(message)
                    pause()

        elif choice == "4":
            save_data()
            display_info_message("Goodbye!")
            break

        else:
            display_error("Invalid choice.")
            pause()


if __name__ == "__main__":
    main()
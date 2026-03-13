# Handles creating, updating, deleting, opening, and closing polls.
# Also handles positions and voting station management.

import datetime
import storage.state as state
from utils.helpers import current_timestamp
from utils.logger import audit_logger
from storage.store import save_data
from utils.constants import MIN_CANDIDATE_AGE, VALID_POSITION_LEVELS


def create_position(form_data: dict):
    title = form_data["title"]
    description = form_data["description"]
    level = form_data["level"]
    max_winners = form_data["max_winners"]
    min_age = form_data.get("min_candidate_age", MIN_CANDIDATE_AGE)
    created_by = form_data["created_by"]

    if level.lower() not in VALID_POSITION_LEVELS:
        return False, "Invalid level. Choose National, Regional or Local."

    if max_winners <= 0:
        return False, "Number of winners must be at least 1."

    created_id = state.position_id_counter

    state.positions[created_id] = {
        "id": created_id,
        "title": title,
        "description": description,
        "level": level.capitalize(),
        "max_winners": max_winners,
        "min_candidate_age": min_age,
        "is_active": True,
        "created_at": current_timestamp(),
        "created_by": created_by,
    }

    audit_logger.log(
        "CREATE_POSITION",
        created_by,
        f"Created position: {title} (ID: {created_id})"
    )

    state.position_id_counter += 1
    save_data()
    return True, f"Position '{title}' created! ID: {created_id}"


def get_all_positions() -> dict:
    return state.positions


def update_position(position_id: int, updates: dict, updated_by: str):
    if position_id not in state.positions:
        return False, "Position not found."

    position = state.positions[position_id]

    if "title" in updates and updates["title"]:
        position["title"] = updates["title"]

    if "description" in updates and updates["description"]:
        position["description"] = updates["description"]

    if "level" in updates and updates["level"]:
        if updates["level"].lower() in VALID_POSITION_LEVELS:
            position["level"] = updates["level"].capitalize()

    if "max_winners" in updates and updates["max_winners"]:
        position["max_winners"] = updates["max_winners"]

    audit_logger.log(
        "UPDATE_POSITION",
        updated_by,
        f"Updated position: {position['title']}"
    )
    save_data()
    return True, "Position updated successfully."


def delete_position(position_id: int, deleted_by: str):
    if position_id not in state.positions:
        return False, "Position not found."

    for poll in state.polls.values():
        for position in poll.get("positions", []):
            if position["position_id"] == position_id and poll["status"] == "open":
                return False, f"Cannot delete - in active poll: {poll['title']}"

    state.positions[position_id]["is_active"] = False

    audit_logger.log(
        "DELETE_POSITION",
        deleted_by,
        f"Deactivated position: {state.positions[position_id]['title']}"
    )
    save_data()
    return True, "Position deactivated."


def create_poll(form_data: dict):
    title = form_data["title"]
    description = form_data["description"]
    election_type = form_data["election_type"]
    start_date = form_data["start_date"]
    end_date = form_data["end_date"]
    selected_positions = form_data["selected_position_ids"]
    selected_stations = form_data["selected_station_ids"]
    created_by = form_data["created_by"]

    try:
        start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        if end_date_obj <= start_date_obj:
            return False, "End date must be after start date."
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD."

    poll_positions = []
    for position_id in selected_positions:
        if position_id not in state.positions:
            continue
        if not state.positions[position_id]["is_active"]:
            continue

        poll_positions.append({
            "position_id": position_id,
            "position_title": state.positions[position_id]["title"],
            "candidate_ids": [],
            "max_winners": state.positions[position_id]["max_winners"],
        })

    if not poll_positions:
        return False, "No valid positions selected."

    created_id = state.poll_id_counter

    state.polls[created_id] = {
        "id": created_id,
        "title": title,
        "description": description,
        "election_type": election_type,
        "start_date": start_date,
        "end_date": end_date,
        "positions": poll_positions,
        "station_ids": selected_stations,
        "status": "draft",
        "total_votes_cast": 0,
        "created_at": current_timestamp(),
        "created_by": created_by,
    }

    audit_logger.log(
        "CREATE_POLL",
        created_by,
        f"Created poll: {title} (ID: {created_id})"
    )

    state.poll_id_counter += 1
    save_data()
    return True, f"Poll '{title}' created! ID: {created_id}"


def get_all_polls() -> dict:
    return state.polls


def get_open_polls() -> dict:
    return {
        poll_id: poll
        for poll_id, poll in state.polls.items()
        if poll["status"] == "open"
    }


def get_closed_polls() -> dict:
    return {
        poll_id: poll
        for poll_id, poll in state.polls.items()
        if poll["status"] == "closed"
    }


def update_poll(poll_id: int, updates: dict, updated_by: str):
    if poll_id not in state.polls:
        return False, "Poll not found."

    poll = state.polls[poll_id]

    if poll["status"] == "open":
        return False, "Cannot update an open poll. Close it first."

    if poll["status"] == "closed" and poll["total_votes_cast"] > 0:
        return False, "Cannot update a poll that already has votes."

    if "title" in updates and updates["title"]:
        poll["title"] = updates["title"]

    if "description" in updates and updates["description"]:
        poll["description"] = updates["description"]

    if "election_type" in updates and updates["election_type"]:
        poll["election_type"] = updates["election_type"]

    if "start_date" in updates and updates["start_date"]:
        try:
            datetime.datetime.strptime(updates["start_date"], "%Y-%m-%d")
            poll["start_date"] = updates["start_date"]
        except ValueError:
            pass

    if "end_date" in updates and updates["end_date"]:
        try:
            datetime.datetime.strptime(updates["end_date"], "%Y-%m-%d")
            poll["end_date"] = updates["end_date"]
        except ValueError:
            pass

    audit_logger.log(
        "UPDATE_POLL",
        updated_by,
        f"Updated poll: {poll['title']}"
    )
    save_data()
    return True, "Poll updated successfully."


def delete_poll(poll_id: int, deleted_by: str):
    if poll_id not in state.polls:
        return False, "Poll not found."

    if state.polls[poll_id]["status"] == "open":
        return False, "Cannot delete an open poll. Close it first."

    deleted_title = state.polls[poll_id]["title"]
    del state.polls[poll_id]

    state.votes = [vote for vote in state.votes if vote["poll_id"] != poll_id]

    audit_logger.log(
        "DELETE_POLL",
        deleted_by,
        f"Deleted poll: {deleted_title}"
    )
    save_data()
    return True, f"Poll '{deleted_title}' deleted."


def open_close_poll(poll_id: int, action_by: str):
    if poll_id not in state.polls:
        return False, "Poll not found.", None

    poll = state.polls[poll_id]

    if poll["status"] == "draft":
        if not any(position["candidate_ids"] for position in poll["positions"]):
            return False, "Cannot open - no candidates assigned.", None

        poll["status"] = "open"
        audit_logger.log("OPEN_POLL", action_by, f"Opened poll: {poll['title']}")
        save_data()
        return True, f"Poll '{poll['title']}' is now OPEN for voting!", "open"

    if poll["status"] == "open":
        poll["status"] = "closed"
        audit_logger.log("CLOSE_POLL", action_by, f"Closed poll: {poll['title']}")
        save_data()
        return True, f"Poll '{poll['title']}' is now CLOSED.", "closed"

    if poll["status"] == "closed":
        poll["status"] = "open"
        audit_logger.log("REOPEN_POLL", action_by, f"Reopened poll: {poll['title']}")
        save_data()
        return True, "Poll reopened!", "open"

    return False, "Unknown poll status.", None


def assign_candidates_to_poll(poll_id: int, position_index: int, candidate_ids: list, assigned_by: str):
    if poll_id not in state.polls:
        return False, "Poll not found."

    poll = state.polls[poll_id]

    if poll["status"] == "open":
        return False, "Cannot modify candidates of an open poll."

    if position_index < 0 or position_index >= len(poll["positions"]):
        return False, "Invalid position selection."

    position = poll["positions"][position_index]
    pos_data = state.positions.get(position["position_id"], {})
    min_age = pos_data.get("min_candidate_age", MIN_CANDIDATE_AGE)

    valid_ids = []
    for candidate_id in candidate_ids:
        if candidate_id in state.candidates:
            candidate = state.candidates[candidate_id]
            if (
                candidate["is_active"]
                and candidate["is_approved"]
                and candidate["age"] >= min_age
            ):
                valid_ids.append(candidate_id)

    position["candidate_ids"] = valid_ids

    audit_logger.log(
        "ASSIGN_CANDIDATES",
        assigned_by,
        f"Updated candidates for poll: {poll['title']}"
    )
    save_data()
    return True, f"{len(valid_ids)} candidate(s) assigned."


def create_station(form_data: dict):
    name = form_data["name"]
    location = form_data["location"]
    region = form_data["region"]
    capacity = form_data["capacity"]
    supervisor = form_data["supervisor"]
    contact = form_data["contact"]
    opening_time = form_data["opening_time"]
    closing_time = form_data["closing_time"]
    created_by = form_data["created_by"]

    if capacity <= 0:
        return False, "Capacity must be a positive number."

    created_id = state.station_id_counter

    state.voting_stations[created_id] = {
        "id": created_id,
        "name": name,
        "location": location,
        "region": region,
        "capacity": capacity,
        "supervisor": supervisor,
        "contact": contact,
        "opening_time": opening_time,
        "closing_time": closing_time,
        "is_active": True,
        "created_at": current_timestamp(),
        "created_by": created_by,
    }

    audit_logger.log(
        "CREATE_STATION",
        created_by,
        f"Created station: {name} (ID: {created_id})"
    )

    state.station_id_counter += 1
    save_data()
    return True, f"Voting Station '{name}' created! ID: {created_id}"


def get_all_stations() -> dict:
    return state.voting_stations


def update_station(station_id: int, updates: dict, updated_by: str):
    if station_id not in state.voting_stations:
        return False, "Station not found."

    station = state.voting_stations[station_id]

    updatable_fields = [
        "name",
        "location",
        "region",
        "capacity",
        "supervisor",
        "contact",
    ]

    for field in updatable_fields:
        if field in updates and updates[field]:
            station[field] = updates[field]

    audit_logger.log(
        "UPDATE_STATION",
        updated_by,
        f"Updated station: {station['name']} (ID: {station_id})"
    )
    save_data()
    return True, f"Station '{station['name']}' updated successfully."


def delete_station(station_id: int, deleted_by: str):
    if station_id not in state.voting_stations:
        return False, "Station not found."

    state.voting_stations[station_id]["is_active"] = False
    station_name = state.voting_stations[station_id]["name"]

    audit_logger.log(
        "DELETE_STATION",
        deleted_by,
        f"Deactivated station: {station_name}"
    )
    save_data()
    return True, f"Station '{station_name}' deactivated."
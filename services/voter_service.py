# Handles voter verification, deactivation, search, and password changes.

import storage.state as state
from utils.helpers import hash_password
from utils.logger import audit_logger
from storage.store import save_data


def get_all_voters() -> dict:
    return state.voters


def get_unverified_voters() -> dict:
    return {
        voter_id: voter
        for voter_id, voter in state.voters.items()
        if not voter["is_verified"]
    }


def verify_voter(voter_id: int, verified_by: str):
    if voter_id not in state.voters:
        return False, "Voter not found."

    if state.voters[voter_id]["is_verified"]:
        return False, "This voter is already verified."

    state.voters[voter_id]["is_verified"] = True
    voter_name = state.voters[voter_id]["full_name"]

    audit_logger.log("VERIFY_VOTER", verified_by, f"Verified voter: {voter_name}")
    save_data()
    return True, f"Voter '{voter_name}' verified successfully."


def verify_all_voters(verified_by: str):
    unverified = get_unverified_voters()

    if not unverified:
        return False, "No unverified voters found."

    count = 0
    for voter_id in unverified:
        state.voters[voter_id]["is_verified"] = True
        count += 1

    audit_logger.log("VERIFY_ALL_VOTERS", verified_by, f"Verified {count} voters")
    save_data()
    return True, f"{count} voters verified successfully."


def deactivate_voter(voter_id: int, deactivated_by: str):
    if voter_id not in state.voters:
        return False, "Voter not found."

    if not state.voters[voter_id]["is_active"]:
        return False, "This voter is already deactivated."

    state.voters[voter_id]["is_active"] = False
    voter_name = state.voters[voter_id]["full_name"]

    audit_logger.log(
        "DEACTIVATE_VOTER",
        deactivated_by,
        f"Deactivated voter: {voter_name}"
    )
    save_data()
    return True, "Voter deactivated successfully."


def search_voters(search_by: str, search_term) -> list:
    if search_by == "name":
        return [
            voter
            for voter in state.voters.values()
            if search_term.lower() in voter["full_name"].lower()
        ]

    if search_by == "card":
        return [
            voter
            for voter in state.voters.values()
            if search_term == voter["voter_card_number"]
        ]

    if search_by == "national_id":
        return [
            voter
            for voter in state.voters.values()
            if search_term == voter["national_id"]
        ]

    if search_by == "station":
        return [
            voter
            for voter in state.voters.values()
            if voter["station_id"] == search_term
        ]

    return []


def change_voter_password(voter_id: int, old_password: str, new_password: str):
    if voter_id not in state.voters:
        return False, "Voter not found."

    voter = state.voters[voter_id]

    if hash_password(old_password) != voter["password"]:
        return False, "Incorrect current password."

    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."

    new_hashed_password = hash_password(new_password)
    voter["password"] = new_hashed_password

    if state.current_user and state.current_user.get("id") == voter_id:
        state.current_user["password"] = new_hashed_password

    audit_logger.log(
        "CHANGE_PASSWORD",
        voter["voter_card_number"],
        "Password changed"
    )
    save_data()
    return True, "Password changed successfully."
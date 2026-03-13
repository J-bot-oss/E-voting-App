# Handles ballot casting, vote recording, and voting history.

import hashlib
import storage.state as state
from utils.helpers import current_timestamp
from utils.logger import audit_logger
from storage.store import save_data


def get_available_polls_for_voter(voter: dict) -> dict:
    """Return polls the voter is allowed to vote in."""
    available = {}

    for poll_id, poll in state.polls.items():
        already_voted = poll_id in voter.get("has_voted_in", [])
        station_allowed = voter["station_id"] in poll["station_ids"]

        if poll["status"] == "open" and not already_voted and station_allowed:
            available[poll_id] = poll

    return available


def cast_vote(voter: dict, poll_id: int, vote_selections: list):
    """Record a voter's vote for a poll."""
    if poll_id not in state.polls:
        return False, "Poll not found.", None

    poll = state.polls[poll_id]

    if poll["status"] != "open":
        return False, "This poll is no longer open.", None

    if poll_id in voter.get("has_voted_in", []):
        return False, "You have already voted in this poll.", None

    vote_timestamp = current_timestamp()
    vote_hash = hashlib.sha256(
        f"{voter['id']}{poll_id}{vote_timestamp}".encode()
    ).hexdigest()[:16]

    for selection in vote_selections:
        state.votes.append(
            {
                "vote_id": vote_hash + str(selection["position_id"]),
                "poll_id": poll_id,
                "position_id": selection["position_id"],
                "candidate_id": selection.get("candidate_id"),
                "voter_id": voter["id"],
                "station_id": voter["station_id"],
                "timestamp": vote_timestamp,
                "abstained": selection.get("abstained", False),
            }
        )

    if poll_id not in voter["has_voted_in"]:
        voter["has_voted_in"].append(poll_id)

    for stored_voter in state.voters.values():
        if stored_voter["id"] == voter["id"]:
            if poll_id not in stored_voter["has_voted_in"]:
                stored_voter["has_voted_in"].append(poll_id)
            break

    poll["total_votes_cast"] += 1

    audit_logger.log(
        "CAST_VOTE",
        voter["voter_card_number"],
        f"Voted in poll: {poll['title']} (Hash: {vote_hash})",
    )

    save_data()
    return True, "Your vote has been recorded successfully.", vote_hash


def get_voting_history(voter: dict) -> list:
    """Return the voting history of a voter."""
    history = []
    voted_poll_ids = voter.get("has_voted_in", [])

    for poll_id in voted_poll_ids:
        if poll_id not in state.polls:
            continue

        poll = state.polls[poll_id]

        voter_votes = [
            vote
            for vote in state.votes
            if vote["poll_id"] == poll_id and vote["voter_id"] == voter["id"]
        ]

        history.append(
            {
                "poll_id": poll_id,
                "poll_title": poll["title"],
                "poll_status": poll["status"],
                "election_type": poll["election_type"],
                "votes": voter_votes,
            }
        )

    return history
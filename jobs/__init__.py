from nautobot.apps.jobs import register_jobs

from .intended_state import IntendedState

register_jobs(IntendedState)

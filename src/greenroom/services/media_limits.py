"""Result-count policy for media retrieval: how many results are returned.

These values are shared by the tool, service, and protocol layers.
This file is placed within the services layer because the tool layer may
import from services, but services must never import from tools.
"""

#-----------------------------
# TMDB-defined  limits
#-----------------------------

# As of 2026, TMDB serves 20 results per page and does not provide an option to the caller to override this.
# These values are covered by external tests so a change in the contract will be discovered.
# Before more content providers are added, PROVIDER_PAGE_SIZE should move to MediaService protocol.

PROVIDER_PAGE_SIZE: int = 20 # number of results a single page returned from the provider can hold

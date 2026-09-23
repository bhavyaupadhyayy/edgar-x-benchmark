"""Study design and statistical conventions for the EDGAR-X feasibility gates.

Flat layout on purpose: these modules import each other as siblings so the
directory survives being zipped, flattened, or copied file by file.
"""

# --- Study design -----------------------------------------------------------

PREDICTION_HORIZON_DAYS = 365
BANKRUPTCY_ITEM_CODE = "1.03"

# XBRL was phased in by filer size: largest filers from 2009, other large
# accelerated filers from 2010, remaining filers only for periods ending on or
# after 15 June 2011. Structured coverage before 2012 is therefore biased
# toward large firms, which is the opposite of where bankruptcies concentrate.
PRIMARY_COHORT_START_YEAR = 2012

# A 10-K needs a full horizon of post-filing observation to be labelable, so
# the last mature cohort ends one horizon before today.
DISCOVERY_START_YEAR = 2001  # EDGAR full-text search coverage begins here

# --- Statistical conventions ------------------------------------------------

ALPHA = 0.05
TARGET_POWER = 0.80

# z_{alpha/2} + z_{power}. Multiply by a standard error for the MDE.
MDE_Z_MULTIPLIER = 2.802

# --- Simulation defaults ----------------------------------------------------

DEFAULT_AP_PIT = 0.15
DEFAULT_SCORE_CORRELATION = 0.90
DEFAULT_FIRM_ICC = 0.30

# Noise draws averaged when solving for the separation that hits a target AP.
# One draw is not enough: at 25 positives the single-draw objective is noisy
# enough to move the calibrated separation, and therefore the simulated true
# effect, by more than the effect being measured.
CALIBRATION_DRAWS = 60

MONTE_CARLO_REPLICATES = 400
RANDOM_SEED = 20260913

# Share of the firm pool replaced each fold, covering exits, delistings and new
# registrants. Only affects how quickly the persistent firm effect turns over.
DEFAULT_FIRM_CHURN_RATE = 0.10

# --- SEC HTTP etiquette -----------------------------------------------------

SEC_USER_AGENT = "EDGAR-X Research bhavya.upadhyay@example.com"
SEC_MAX_REQUESTS_PER_SECOND = 8

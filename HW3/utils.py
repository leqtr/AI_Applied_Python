from typing import Optional
from datetime import datetime
import string, random, json

### HELPERS
def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt

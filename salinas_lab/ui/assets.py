from __future__ import annotations

from salinas_lab.graph import DepartmentName

LAB_SIGN = r"""
  .================================================================.
  |                                                                |
  |   O P E N L O G O S   L A B                                    |
  |   Applied Curiosity Containment Facility                       |
  |                                                                |
  |   "Progress Through Questionable Confidence                    |
  |    and Excellent Documentation."                               |
  |                                                                |
  '================================================================'
"""


COMMAND_CENTER_ART = r"""
             _________________________________
            /  FOUNDER CONSOLE               /|
           /_________________________________/ |
           |  [CHAT]  Board Room             | |
           |  [R&D ]  Full Facility Wake     | |
           |  [MEM ]  Institutional Memory   | |
           |                                 | |
           |  NOTICE: all ideas are handled  | |
           |  with gloves, goggles, and logs.| /
           |_________________________________|/
"""


FACILITY_ART = r"""
                 /\                         OpenLogos Lab
                /  \              Applied Curiosity Containment
       ________/____\________
      |  OBS  |  SCT  |  SCI |
      |_______|_______|______|
      |  PRD  |  TST  |  RSK |
      |_______|_______|______|
      |       PUBLICATIONS   |
      |______________________|
          |  IDEA INTAKE  |
          |_______________|
"""


DEPARTMENT_LABELS = {
    DepartmentName.DIRECTOR: "Director Office",
    DepartmentName.OPPORTUNITY_DISCOVERY: "Opportunity Discovery",
    DepartmentName.SCIENTIFIC_INQUIRY: "Scientific Inquiry",
    DepartmentName.PRODUCT_APPLICATIONS: "Product Applications",
    DepartmentName.HUMAN_TESTING: "Human Testing",
    DepartmentName.RISK_ETHICS: "Risk and Ethics",
    DepartmentName.PUBLICATIONS: "Publications",
}


DEPARTMENT_ICONS = {
    DepartmentName.DIRECTOR: "OBS",
    DepartmentName.OPPORTUNITY_DISCOVERY: "SCT",
    DepartmentName.SCIENTIFIC_INQUIRY: "SCI",
    DepartmentName.PRODUCT_APPLICATIONS: "PRD",
    DepartmentName.HUMAN_TESTING: "TST",
    DepartmentName.RISK_ETHICS: "RSK",
    DepartmentName.PUBLICATIONS: "PUB",
}


DEPARTMENT_COLORS = {
    DepartmentName.DIRECTOR: "bright_blue",
    DepartmentName.OPPORTUNITY_DISCOVERY: "bright_cyan",
    DepartmentName.SCIENTIFIC_INQUIRY: "bright_white",
    DepartmentName.PRODUCT_APPLICATIONS: "bright_green",
    DepartmentName.HUMAN_TESTING: "yellow",
    DepartmentName.RISK_ETHICS: "orange3",
    DepartmentName.PUBLICATIONS: "magenta",
}


BUILDING_WINDOWS = {
    DepartmentName.DIRECTOR: (1, 1),
    DepartmentName.OPPORTUNITY_DISCOVERY: (1, 2),
    DepartmentName.SCIENTIFIC_INQUIRY: (2, 1),
    DepartmentName.PRODUCT_APPLICATIONS: (2, 2),
    DepartmentName.HUMAN_TESTING: (3, 1),
    DepartmentName.RISK_ETHICS: (3, 2),
    DepartmentName.PUBLICATIONS: (4, 1),
}


def status_bubble(message: str) -> str:
    return f"({message})"

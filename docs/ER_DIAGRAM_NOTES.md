# Police FIR ER Diagram Notes

## Overview

Summary of the Karnataka Police FIR database schema.

### Central Entity

-   CaseMaster

### Connected Entities

-   Victim
-   Accused
-   ComplainantDetails
-   ArrestSurrender
-   ChargesheetDetails
-   Act
-   Section
-   CrimeHead
-   CrimeSubHead
-   Employee
-   Unit
-   Court
-   District
-   State

### Key Insights

-   CaseMaster is the hub.
-   One FIR can have many victims, accused, complainants and arrests.
-   Existing schema supports conversational AI, graph analysis,
    analytics and profiling.
-   Investigation workflow and deadline management are not present and
    can be added as an extension.

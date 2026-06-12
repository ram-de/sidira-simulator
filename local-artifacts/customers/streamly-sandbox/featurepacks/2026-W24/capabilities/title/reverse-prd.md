### 1. User goal
The user goal is to view detailed information about a title on Streamly.

### 2. Roles
The observed roles are:
* member
* premium

### 3. Flow per role
Both member and premium roles can access the title details page via the `/title/:id` route. The flow involves:
- Viewing the title details dialog with headings such as "The Coral Architects / Drama / Sci-Fi / Documentary"
- Optionally adding the title to their list by clicking the '+ My List' button
- Scrolling through the feed to view more information
- Exiting the dialog by clicking the '✕' button to return to the browse page or clicking the '▶ Play' link to start watching the title

The premium role has additional information displayed, such as "4K Ultra HD", but the overall flow remains the same.

### 4. Success criteria
Success criteria include:
- The title details dialog is displayed with the correct information
- The user can add the title to their list successfully
- The user can scroll through the feed without issues
- The user can exit the dialog and navigate to other pages (browse or watch) successfully

### 5. Edge cases & failure modes
Edge cases and failure modes include:
- The user clicking the '+ My List' button when the title is already in their list
- The user scrolling through the feed when there is no more content to display
- The user clicking the '✕' button or '▶ Play' link when the dialog is not fully loaded
- The user not having permission to access the title details page

### 6. Dependencies
Dependencies include:
- The browse capability (`/browse::s875413`) for exiting the title details dialog
- The watch capability (`/watch/:id::overlay+s002039`) for starting to watch the title

### 7. Implicit metric
Implicit metric includes:
- The number of times users click the '+ My List' button to add titles to their list
- The number of times users start watching a title from the title details dialog
- The time spent by users on the title details page before exiting or taking another action
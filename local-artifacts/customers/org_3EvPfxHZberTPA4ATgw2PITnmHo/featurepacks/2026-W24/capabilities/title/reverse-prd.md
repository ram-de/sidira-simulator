### 1. User goal
The user goal is to view details about a specific title on Streamly.

### 2. Roles
The observed roles are:
* member
* premium

### 3. Flow per role
Both member and premium roles can access the title details page via the `/title/:id` route. The flow involves:
1. Landing on the title details page with a dialog overlay, displaying headings such as "The Coral Architects / Drama / Sci-Fi / Documentary" and copy including "STREAMLY | Browse | Search | My List | Kids | [User Name] | Sign Out | Featured".
2. For both roles, clicking the '+ My List' button transitions to another dialog overlay (`/title/:id::overlay+dialog+sd93668`).
3. For both roles, scrolling the feed transitions to an exhausted dialog overlay (`/title/:id::overlay+dialog+exhausted+s6f169a`).
4. Unique to the premium role, the title details page may display additional information such as "4K Ultra HD".

### 4. Success criteria
Success criteria include:
* The title details page loads correctly with the expected headings and copy.
* The '+ My List' button functions as expected, adding the title to the user's list.
* The scroll feed functionality works as expected, transitioning to the exhausted dialog overlay.
* The '✕' button and '▶ Play' link function correctly, exiting the title details page and navigating to the browse page or watch page, respectively.

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The title details page capability depends on the following capabilities:
* Browse capability (`/browse::s875413`): The user can exit the title details page by clicking the '✕' button and navigate to the browse page.
* Watch capability (`/watch/:id::overlay+s002039`): The user can exit the title details page by clicking the '▶ Play' link and navigate to the watch page.

### 7. Implicit metric
_(no evidence observed)_
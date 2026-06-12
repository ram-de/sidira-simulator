### 1. User goal
The user goal is to view details about a specific title on Streamly.

### 2. Roles
The observed roles are:
* member
* premium

### 3. Flow per role
Both member and premium roles can access the title details page via the `/title/:id` route. The flow involves:
* Viewing the title details dialog with headings such as "The Coral Architects / Drama / Sci-Fi / Documentary" and copy including "STREAMLY | Browse | Search | My List | Kids | Sam Member | Sign Out | Featured"
* Clicking the '+ My List' button to add the title to their list
* Scrolling through the feed to view more information
* Clicking the '✕' button to exit the dialog and return to the browse page
* Clicking the '▶ Play' link to start watching the title

The premium role also has access to additional information such as "4K Ultra HD" for certain titles.

### 4. Success criteria
Success criteria include:
* The user can view the title details dialog with relevant information such as genre and headings
* The user can add the title to their list by clicking the '+ My List' button
* The user can scroll through the feed to view more information
* The user can exit the dialog and return to the browse page by clicking the '✕' button
* The user can start watching the title by clicking the '▶ Play' link

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The title details capability depends on the following capabilities:
* Browse capability (`/browse::s875413`): the user can exit the title details dialog and return to the browse page
* Watch capability (`/watch/:id::overlay+s002039`): the user can start watching the title by clicking the '▶ Play' link

### 7. Implicit metric
_(no evidence observed)_
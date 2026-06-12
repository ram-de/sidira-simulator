### 1. User goal
The user goal is to view details about a specific title on Streamly.

### 2. Roles
The observed roles are:
* member
* premium

### 3. Flow per role
Both member and premium roles can access the title details page via the `/title/:id` route. The flow involves:
* Viewing the title details dialog with headings such as "The Coral Architects / Drama / Sci-Fi / Documentary" and copy including "STREAMLY | Browse | Search | My List | Kids | Sam Member | Sign Out | Featured"
* Clicking the '+ My List' button to transition to another dialog (`/title/:id::overlay+dialog+sd93668`)
* Scrolling the feed to transition to an exhausted dialog (`/title/:id::overlay+dialog+exhausted+s6f169a`)
* Premium users may also see additional information such as "4K Ultra HD"

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The title details capability depends on the following capabilities:
* Browse (`/browse::s875413`): accessed when the user clicks the '✕' button
* Watch (`/watch/:id::overlay+s002039`): accessed when the user clicks the '▶ Play' link

### 7. Implicit metric
_(no evidence observed)_
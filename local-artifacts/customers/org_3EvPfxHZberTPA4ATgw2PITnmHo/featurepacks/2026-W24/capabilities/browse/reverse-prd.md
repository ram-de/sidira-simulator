### 1. User goal
The user goal is to browse available content on Streamly, as indicated by the copy "Browse" on the `/browse` screens.

### 2. Roles
The observed roles are:
* guest
* member
* premium

### 3. Flow per role
* **Guest**: The guest role can access the `/browse` screen and scroll through the feed, transitioning to `/browse::exhausted+s875413`.
* **Member**: The member role can access the `/browse` screen, scroll through the feed, and click on links such as "STREAMLY", "Browse", "Search", "My List", "Kids", and "Sign Out". They can also click on specific titles to access more information or play the content.
* **Premium**: The premium role has similar capabilities to the member role, with the addition of accessing 4K Ultra HD content.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The browse capability depends on the following capabilities:
* Search (`/search`)
* My List (`/my-list`)
* Kids (`/kids`)
* Account (`/account`)
* Watch (`/watch/:id`)
* Title (`/title/:id`)

### 7. Implicit metric
The implicit metric for the browse capability could be the number of titles clicked or played, as well as the amount of time spent browsing the `/browse` screens.
### 1. User goal
The user goal is to browse available content on Streamly, as indicated by the copy "Browse" on the `/browse` screens.

### 2. Roles
The observed roles are:
* guest
* member
* premium

### 3. Flow per role
#### Guest
The guest role can access the `/browse` screen, but the specific flow is not well-defined, as there are no unique transitions or exits observed for the guest role.

#### Member
The member role can access the `/browse` screen and navigate through different screens, such as `/browse::s633472`, `/browse::exhausted+s875413`, and `/browse::s875413`. The member can also click on links like "Search", "My List", "Kids", and "Sign Out".

#### Premium
The premium role has a similar flow to the member role, with access to the same screens and links. Additionally, the premium role can click on the link "Pat Premium" to access the account screen.

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
* Watch (`/watch`)
* Title (`/title`)

### 7. Implicit metric
The implicit metric for the browse capability could be the number of times a user navigates through the different browse screens, or the number of clicks on links like "Search", "My List", and "Kids". Additionally, the time spent on the browse screens could be a metric to measure user engagement.
### 1. User goal
The user goal is to browse available content on Streamly, as indicated by the copy "Browse" on the `/browse` screens.

### 2. Roles
The observed roles are:
* guest
* member
* premium

### 3. Flow per role
#### Guest
The guest role can access the `/browse` screen, but the specific flow is not well-defined, as there are no observed transitions or exits specific to the guest role.

#### Member
The member role can access the `/browse` screen and navigate through different screens, such as `/browse::s633472`, `/browse::exhausted+s875413`, and `/browse::s875413`. They can also exit into other capabilities, such as `/search`, `/my-list`, `/kids`, `/account`, and `/watch`.

#### Premium
The premium role has a similar flow to the member role, with access to the same `/browse` screens and exits into other capabilities. Additionally, they have a unique screen `/browse::s2ae585` with a heading "4K Ultra HD".

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
The implicit metric for the browse capability could be the number of times a user navigates through the `/browse` screens or exits into other capabilities, such as clicking on the "▶ Play" link or accessing the "More Info" dialog. However, without more information, it is difficult to define a specific metric.
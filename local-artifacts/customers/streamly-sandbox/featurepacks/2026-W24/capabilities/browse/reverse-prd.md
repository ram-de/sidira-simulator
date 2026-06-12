### 1. User goal
The user goal is to browse and discover content on Streamly.

### 2. Roles
The observed roles are:
- guest
- member
- premium

### 3. Flow per role
#### Guest
- The guest starts on the `/browse::s633472` screen.
- The guest can scroll through the feed to reach the `/browse::exhausted+s875413` screen.
- From the `/browse::exhausted+s875413` screen, the guest can click on the 'STREAMLY' or 'Browse' links to navigate to other screens, but the specific destination screens are not observed for the guest role.

#### Member
- The member starts on various `/browse` screens (e.g., `/browse::s633472`, `/browse::sbc5c3a`, `/browse::s875413`, `/browse::s2c425e`, `/browse::sc764aa`).
- The member can scroll through the feed to reach the exhausted screens (e.g., `/browse::exhausted+s875413`, `/browse::exhausted+sc764aa`).
- From the exhausted screens, the member can click on the 'STREAMLY' or 'Browse' links to navigate to other `/browse` screens.
- The member can also click on links to exit into other capabilities, such as 'Search', 'My List', 'Kids', 'Account', 'Sign Out', 'Play', 'More Info', and specific title links.

#### Premium
- The premium user starts on various `/browse` screens (e.g., `/browse::s633472`, `/browse::sbc5c3a`, `/browse::s875413`, `/browse::s2c425e`, `/browse::sc764aa`, `/browse::s2ae585`).
- The premium user can scroll through the feed to reach the exhausted screens (e.g., `/browse::exhausted+s875413`, `/browse::exhausted+sc764aa`).
- From the exhausted screens, the premium user can click on the 'STREAMLY' or 'Browse' links to navigate to other `/browse` screens.
- The premium user can also click on links to exit into other capabilities, such as 'Search', 'My List', 'Kids', 'Account', 'Sign Out', 'Play', 'More Info', and specific title links.
- The premium user has an additional link '4K' on some screens.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The browse capability depends on the following capabilities:
- Search
- My List
- Kids
- Account
- Watch
- Title

### 7. Implicit metric
_(no evidence observed)_
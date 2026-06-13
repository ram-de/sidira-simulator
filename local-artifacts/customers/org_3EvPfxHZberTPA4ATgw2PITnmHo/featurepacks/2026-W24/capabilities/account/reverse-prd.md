### User goal
Manage my Streamly account settings.

### Roles
* member
* premium

### Flow per role
#### member
1. The member lands on the `/account::s4058eb` screen, which displays headings for Account, Membership, Playback settings, and Security.
2. The member can click the 'Accept' button to transition to the `/account::saca983` screen.
3. From either the `/account::s4058eb` or `/account::saca983` screen, the member can click links to navigate to other capabilities, such as `/browse`, `/search`, `/my-list`, `/kids`, or `/account/plan`.
4. The member can also sign out of their account by clicking the 'Sign Out' or 'Sign out of Streamly' button.

#### premium
1. The premium user lands on the `/account::s4058eb` screen, which displays headings for Account, Membership, Playback settings, and Security.
2. The premium user can click the 'Accept' button to transition to the `/account::saca983` screen.
3. From either the `/account::s4058eb` or `/account::saca983` screen, the premium user can click links to navigate to other capabilities, such as `/browse`, `/search`, `/my-list`, `/kids`, or `/account/plan`.
4. The premium user can also sign out of their account by clicking the 'Sign Out' or 'Sign out of Streamly' button.

### Success criteria
_(no evidence observed)_

### Edge cases & failure modes
_(no evidence observed)_

### Dependencies
The account capability depends on the following capabilities:
* `/browse`
* `/search`
* `/my-list`
* `/kids`
* `/account/plan`
* Sign out functionality (`/::sfb8cd5`, `/::scdffb1`)

### Implicit metric
_(no evidence observed)_
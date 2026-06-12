### User goal
Manage my Streamly account settings.

### Roles
* member
* premium

### Flow per role
#### Member
1. The member lands on the `/account::s4058eb` screen, which displays headings for Account, Membership, Playback settings, and Security.
2. The member can click the 'Accept' button to transition to the `/account::saca983` screen.
3. From either the `/account::s4058eb` or `/account::saca983` screen, the member can click links to navigate to other capabilities, such as Browse, Search, My List, Kids, or manage their plan.
4. The member can also sign out of their account by clicking the 'Sign Out' or 'Sign out of Streamly' button.

#### Premium
1. The premium user lands on the `/account::s4058eb` screen, which displays headings for Account, Membership, Playback settings, and Security.
2. The premium user can click the 'Accept' button to transition to the `/account::saca983` screen.
3. From either the `/account::s4058eb` or `/account::saca983` screen, the premium user can click links to navigate to other capabilities, such as Browse, Search, My List, Kids, or manage their plan.
4. The premium user can also sign out of their account by clicking the 'Sign Out' or 'Sign out of Streamly' button.

### Success criteria
_(no evidence observed)_

### Edge cases & failure modes
_(no evidence observed)_

### Dependencies
The account capability depends on the following capabilities:
* Browse (`/browse::s875413`, `/browse::s633472`, `/browse::sbc5c3a`)
* Search (`/search::sf0043e`, `/search::se78740`)
* My List (`/my-list::s7709ba`, `/my-list::s329ed6`)
* Kids (`/kids::s7709ba`, `/kids::s329ed6`)
* Account plan management (`/account/plan::se5de17`, `/account/plan::s230757`, `/account/plan::s633472`)
* Sign out (`/::sfb8cd5`, `/::scdffb1`)

### Implicit metric
_(no evidence observed)_
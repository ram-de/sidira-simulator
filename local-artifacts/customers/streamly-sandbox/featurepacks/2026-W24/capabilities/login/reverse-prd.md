### User goal
Log in to an existing Streamly account.

### Roles
The following roles are observed to interact with the login capability:
* guest
* member
* premium

### Flow per role
#### Guest
1. The guest user lands on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The guest user can click on the 'STREAMLY' link to navigate to the `/::sfb8cd5` or `/::scdffb1` screen.
3. The guest user can click on the 'Help' link to navigate to the `/help::sdfec15` or `/help::s9ca1b4` screen.
4. The guest user can click on the 'Sign up now' link to navigate to the `/signup::s2a640d` or `/signup::s8b8d39` screen.
5. If the guest user clicks the 'Accept' button on the `/login::login+s142a09` screen, they are transitioned to the `/login::login+sabcaae` screen.

#### Member
1. The member user lands on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The member user submits the login form, which transitions them to the `/profiles::chooser+sab6eb8` or `/profiles::chooser+s157f95` screen.

#### Premium
1. The premium user lands on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The premium user submits the login form, which transitions them to the `/profiles::chooser+se8c8c0` or `/profiles::chooser+sdb9b57` screen.

### Success criteria
_(no evidence observed)_

### Edge cases & failure modes
_(no evidence observed)_

### Dependencies
The login capability has dependencies on the following capabilities:
* Help (`/help::sdfec15` and `/help::s9ca1b4`)
* Sign up (`/signup::s2a640d` and `/signup::s8b8d39`)
* Profiles (`/profiles::chooser+sab6eb8`, `/profiles::chooser+s157f95`, `/profiles::chooser+se8c8c0`, and `/profiles::chooser+sdb9b57`)

### Implicit metric
_(no evidence observed)_
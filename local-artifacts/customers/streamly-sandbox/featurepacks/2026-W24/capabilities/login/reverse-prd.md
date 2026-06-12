### User goal
Log in to an existing Streamly account.

### Roles
The following roles are observed to interact with the login capability:
- guest
- member
- premium

### Flow per role
#### Guest
1. The guest lands on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The guest can click on the 'STREAMLY' link to exit to `/::sfb8cd5` or `/::scdffb1`.
3. The guest can click on the 'Help' link to exit to `/help::sdfec15` or `/help::s9ca1b4`.
4. The guest can click on the 'Sign up now' link to exit to `/signup::s2a640d` or `/signup::s8b8d39`.
5. If the guest clicks the 'Accept' button on `/login::login+s142a09`, they transition to `/login::login+sabcaae`.

#### Member
1. The member lands on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The member submits the login form, which takes them to `/profiles::chooser+sab6eb8` or `/profiles::chooser+s157f95`.

#### Premium
1. The premium user lands on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The premium user submits the login form, which takes them to `/profiles::chooser+se8c8c0` or `/profiles::chooser+sdb9b57`.

### Success criteria
_(no evidence observed)_

### Edge cases & failure modes
_(no evidence observed)_

### Dependencies
The login capability depends on the following capabilities:
- `/help` (linked from the login screen)
- `/signup` (linked from the login screen)
- `/profiles` (exited to after successful login)

### Implicit metric
_(no evidence observed)_
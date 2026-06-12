### 1. User goal
Find answers to common questions about Streamly.

### 2. Roles
The following roles are observed to use the help capability: 
- guest
- member
- premium

### 3. Flow per role
All roles (guest, member, premium) follow the same flow:
1. Enter the `/help` screen, which displays the "Help Center" with headings and copy including "Quick answers to common questions."
2. The user can then click the 'Accept' button to transition to another `/help` screen (`/help::s9ca1b4`) with the same headings and similar copy.
3. From either `/help` screen, users can click links to exit into other capabilities, such as the main Streamly page (`/::sfb8cd5` or `/::scdffb1`) or the login page (`/login::login+s142a09` or `/login::login+sabcaae`).

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The help capability depends on the following capabilities:
- Main Streamly page (`/::sfb8cd5` and `/::scdffb1`), accessible by clicking the 'STREAMLY' link.
- Login page (`/login::login+s142a09` and `/login::login+sabcaae`), accessible by clicking the 'Sign In' link.

### 7. Implicit metric
_(no evidence observed)_
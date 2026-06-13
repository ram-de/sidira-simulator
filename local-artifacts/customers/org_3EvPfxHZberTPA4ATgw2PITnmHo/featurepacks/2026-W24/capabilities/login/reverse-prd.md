### 1. User goal
Log in to an existing Streamly account.

### 2. Roles
The following roles are observed to interact with the login capability: 
- guest
- member
- premium

### 3. Flow per role
#### Guest
1. The guest starts on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The guest can click on the 'Accept' button to transition between `/login::login+s142a09` and `/login::login+sabcaae`.
3. The guest can exit the login capability by clicking on links to other capabilities, such as 'STREAMLY', 'Help', or 'Sign up now'.

#### Member
1. The member starts on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The member submits the login form, which redirects them to the `/profiles::chooser+sab6eb8` or `/profiles::chooser+s157f95` screen.

#### Premium
1. The premium user starts on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The premium user submits the login form, which redirects them to the `/profiles::chooser+se8c8c0` or `/profiles::chooser+sdb9b57` screen.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The login capability has dependencies on the following capabilities:
- The capability linked to by 'STREAMLY'
- The 'Help' capability
- The 'Sign up' capability
- The 'profiles' capability

### 7. Implicit metric
_(no evidence observed)_
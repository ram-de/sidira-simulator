### 1. User goal
The user goal is to manage account settings and plans on Streamly, including updating membership and playback settings, and reviewing security information.

### 2. Roles
The observed roles are:
- Member
- Premium

### 3. Flow per role
#### Member
1. The member starts at the `/account::s4058eb` screen.
2. They can click the 'Manage plan' link to navigate to the `/account/plan::se5de17` screen.
3. From the `/account/plan::se5de17` screen, they can click the 'Sam Member' link to return to the `/account::s4058eb` screen.
4. They can also click the 'Upgrade to Premium' button to navigate to the `/account/plan::s4de81d` screen.
5. Alternatively, they can click the 'Accept' button on the `/account::s4058eb` screen to navigate to the `/account::saca983` screen.
6. From the `/account::saca983` screen, they can click the 'Manage plan' link to navigate to the `/account/plan::s230757` screen.

#### Premium
1. The premium user starts at the `/account::s4058eb` screen.
2. They can click the 'Manage plan' link to navigate to the `/account/plan::s633472` screen.
3. From the `/account/plan::s633472` screen, they can click the 'Pat Premium' link to return to the `/account::s4058eb` screen.
4. They can also click the 'Accept' button to navigate to the `/account/plan::sbc5c3a` screen.
5. From the `/account/plan::sbc5c3a` screen, they can click the 'Pat Premium' link to navigate to the `/account::saca983` screen.
6. From the `/account::saca983` screen, they can click the 'Manage plan' link to navigate to the `/account/plan::sbc5c3a` screen.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The account capability depends on the following capabilities:
- Browse
- Search
- My List
- Kids
- Sign Out

The account capability can exit into these capabilities through various links and buttons.

### 7. Implicit metric
_(no evidence observed)_
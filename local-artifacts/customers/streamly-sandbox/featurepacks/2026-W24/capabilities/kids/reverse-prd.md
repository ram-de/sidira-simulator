### 1. User goal
The user goal is to access kid-friendly content on Streamly, as indicated by the copy "Shows rated for younger viewers" on the `/kids` screen.

### 2. Roles
The observed roles are:
* `member`
* `premium`

### 3. Flow per role
Both `member` and `premium` roles have the same flow:
1. Enter the `/kids` screen, which displays kid-friendly content.
2. From the `/kids` screen, users can click on links to navigate to other screens, such as:
	* `/browse`
	* `/search`
	* `/my-list`
	* `/account` (for profile management)
	* `/title/:id` (to view specific title details)
3. Users can also sign out by clicking the "Sign Out" button.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The kids capability depends on the following capabilities:
* `/browse`
* `/search`
* `/my-list`
* `/account`
* `/title/:id`
These dependencies are observed through the links and transitions from the `/kids` screen to these other screens.

### 7. Implicit metric
_(no evidence observed)_
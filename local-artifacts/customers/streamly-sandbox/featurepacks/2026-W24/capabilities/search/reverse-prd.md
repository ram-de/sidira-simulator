### User goal
Search for specific content on Streamly.

### Roles
* member
* premium

### Flow per role
#### member
1. The member lands on the `/search::sf0043e` screen.
2. The member sees the headings "Search" and copy "STREAMLY | Browse | Search | My List | Kids | Sam Member | Sign Out | Titles, genres, descriptions."
3. The member can click on links to navigate to other capabilities:
	* "STREAMLY" to `/browse::s2c425e`
	* "Browse" to `/browse::s2c425e`
	* "My List" to `/my-list::s7709ba`
	* "Kids" to `/kids::s7709ba`
	* "Sam Member" to `/account::s4058eb`
	* "Sign Out" to `/::sfb8cd5`
	* Various title links (e.g., "/title/t-108", "/title/t-107", etc.) to `/title/:id::overlay+dialog+s0910b3`

#### premium
1. The premium user lands on either the `/search::sf0043e` or `/search::se78740` screen.
2. The premium user sees the headings "Search" and copy "STREAMLY | Browse | Search | My List | Kids | Pat Premium | Sign Out | Titles, genres, descriptions."
3. The premium user can click on links to navigate to other capabilities:
	* From `/search::sf0043e`:
		+ "STREAMLY" to `/browse::s2c425e`
		+ "Browse" to `/browse::s2c425e`
		+ "My List" to `/my-list::s7709ba`
		+ "Kids" to `/kids::s7709ba`
		+ "Pat Premium" to `/account::s4058eb`
		+ "Sign Out" to `/::sfb8cd5`
		+ Various title links (e.g., "/title/t-108", "/title/t-107", etc.) to `/title/:id::overlay+dialog+s0910b3`
	* From `/search::se78740`:
		+ "STREAMLY" to `/browse::s2ae585`
		+ "Browse" to `/browse::s2ae585`
		+ "My List" to `/my-list::s329ed6`
		+ "Kids" to `/kids::s329ed6`
		+ "Pat Premium" to `/account::saca983`
		+ "Sign Out" to `/::scdffb1`
		+ Various title links (e.g., "4K") to `/title/:id::overlay+dialog+s1b7577`

### Success criteria
_(no evidence observed)_

### Edge cases & failure modes
_(no evidence observed)_

### Dependencies
The search capability depends on the following capabilities:
* Browse (`/browse::s2c425e`, `/browse::s2ae585`)
* My List (`/my-list::s7709ba`, `/my-list::s329ed6`)
* Kids (`/kids::s7709ba`, `/kids::s329ed6`)
* Account (`/account::s4058eb`, `/account::saca983`)
* Title (`/title/:id::overlay+dialog+s0910b3`, `/title/:id::overlay+dialog+s1b7577`)

### Implicit metric
_(no evidence observed)_
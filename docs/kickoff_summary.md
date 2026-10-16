# Neeley AI Forward Kickoff: Summary (Fri Oct 16 2026, 3:00 to 3:47 pm CT)

Sources: whisper transcript of the kickoff Zoom and 80 screen captures. [inf] = inference, [?] = garbled or uncertain.

## 1. Bottom line
- Pharma case (Advanced) = automate competitive intelligence from **10-K filings**: compare a company's products against two competitors' products, track **loss of exclusivity** and **pricing changes**, and turn it into a **strategy stance for the CEO**.
- The sponsor is a pharma company tied to an AI Forward **board member**; Dr. Zain Ali said "go look at the board members" for a hint. Board members tied to pharma: Robby Dally and Jackie Njoroge (McKesson), plus an Alcon fellow. [inf] Unconfirmed; McKesson distributes rather than makes drugs.
- Full case docs drop **Sat 9:00 to 9:20 am**; tonight we only have the teaser.
- Hard deadline **Sun Oct 18, 2:00 pm CDT** on Devpost, video required, then a live laptop demo **2:00 to 4:00 pm** science-fair style.
- Every speaker said the same thing: **business problem and end user first, technology second**. Ali explicitly invited teams to "expand the scope" and "differentiate yourself."

## 2. The five cases
**Advanced: Pharmaceutical (our case).** "A business challenge that was initiated by a pharmaceutical company that is with somebody on the board." Current workflow: "somebody actually goes through the 10K filings and they basically look at the financial numbers and see how their company is compared to the other companies that might be competing on some products." They compare "product A from company one" against "company B and C and their products," and look for "when is the product coming off exclusivity? When does the pricing change and so forth?" Ask: compare "the products from one company to two other companies," find "details... that will give them a competitive advantage," and recommend "how should they create their strategy or how should they take their stance... to the CEO." Data stated so far: 10-K filings only; everything else arrives Saturday. Deliverable: a working prototype plus a CEO-facing strategy output. [inf]

**Advanced: Neeley Advising.** Designed by a student in Ali's graduate Leading Business Transformation class. Students miss options (minors, certificates). Tool vision: take career interests, recommend courses, then use registrar schedule data and time preferences to suggest sections and enroll directly.

**Emerging: Supply Chain Sales.** Built with the Center for Supply Chain and a board member who runs a marketing company. A freight broker needs clients: research "two or three" target accounts, their executives, competitors and products so sales is ready to pitch.

**Emerging: Finance (GL).** Built with board member Parrish Gunnels's firm [?]. Some general ledger entries "fall out": catch them, then recommend corrective action.

**Emerging: TCU Recruitment.** Beat ATS resume filters: find jobs by keyword, tailor the resume and cover letter "to pass through the bot test," and let the user review before submitting.

## 3. Tracks and prizes
- Slide: "Five Cases and Seven Awards in Two Tracks." Advanced: Pharmaceutical, Neeley Advising. Emerging: Supply Chain Sales, Finance (GL), TCU Recruitment.
- Prizes: Advanced $1,500 and $1,000; Emerging $1,000 and $675; "$10,000 total prize pool." Ali said these are awarded **per case** ("for each one of the two cases, somebody is going to walk up with $1,500"), which would mean 10 awards. That conflicts with "Seven Awards" on the slide [?].
- No formal Emerging vs Advanced definition was given. [inf] Advanced means the more technical cases.

## 4. Judging
- The judging criteria slide was shown but not captured. Kayleigh Nava will post the rubric to Microsoft Teams.
- Ali: the rubric rewards taking "something from a concept to a prototype" as a team in one weekend.
- Sunday 2:00 to 4:00 pm showcase: laptops open, "AI fair" style; teams also walk around. Awards 4:30 to 5:00 pm. Time per team not stated.
- Judges: Dallas AI members, board members and industry volunteers, plus the "genius bar" technical advisors. No individual judges named.

## 5. Submission and rules
- Devpost deadline **Oct 18 2026, 2:00 pm CDT**. 64 participants.
- Fields: project name (60 characters); elevator pitch (200 characters); thumbnail (JPG/PNG/GIF, 5 MB, 3:2); "About the project" in Markdown (inspiration, what you learned, how you built it, challenges); image gallery; video demo link; per-member contribution; Terms checkbox.
- Video: "We just want a video showcasing the product." Length not stated.
- Tool restrictions and pre-built code policy not mentioned; Devpost rules require disclosing existing resources.
- Our Devpost project "Advanced Pharmaceuticals" exists as a draft (2 of 4 steps done). Parker was invited.

## 6. Logistics
- Saturday, Neeley 2303 A/B (second-floor banquet room): 8:30 check-in and breakfast; 9:00 to 9:20 case launch; 9:20 to 10:15 build and mentor assignments; 10:30 to 12:00 optional AI tool workshops; 12:00 to 1:00 lunch; 1:00 to 5:30 build with mentors; 5:30 to 6:00 progress check; 6:00 dinner.
- Study rooms bookable on the day until 10 pm; building unlocked for TCU students.
- Sunday: no room reservations, build anywhere; light snacks.
- Each team gets an assigned mentor; unassigned technical advisors sit at a central "genius bar."
- Contacts: Kayleigh Nava, neeleyaiforward@tcu.edu. Will Drover will be away in San Antonio.

## 7. Advice from speakers
- **Zain Ali:** "it's never about the technology. Technology typically always works." Understand the business challenge, make the user journey good, and "don't limit it to what's written in the case... expand the scope... differentiate yourself."
- **Michael Sherrod** (Entrepreneur-in-Residence): "don't let the judges become your customer"; build something you would keep working on.
- **Michael Cupps** (enterprise software, six exits): "your customer is your use case and the outcomes they're associated with"; work backward from the outcome.
- **David Garcia** (CBRE, Senior Enterprise Architect): catalog your biggest assumption and validate at least one.
- **Arun Prakash** (Capgemini): the simple solution won; connect the technology to people.
- A Dell mentor working on logistics modernization with agentic AI is bringing 4 to 5 Dell colleagues.

## 8. Implications for our pharma Advanced plan [inf]
1. User = the competitive-intelligence analyst who reads 10-Ks today; buyer = the CEO. Metric: hours of 10-K reading becomes minutes, with citations.
2. Pull real data live: SEC EDGAR full-text and XBRL financials for the focal company and two competitors, plus FDA Orange Book (patents and exclusivity) and Purple Book (biologics) for **exclusivity cliff dates**. This is the scope expansion Ali invited.
3. Output a one-page **CEO strategy memo** with a clear stance (defend, price, partner, pivot), every claim linked to a filing passage. Parker owns the financial logic and memo voice.
4. Show a product-by-product comparison table plus a timeline of LOE and pricing events: the visual hook for walk-up judging.
5. Keep the code generic so any three tickers work; pre-load likely examples only until Saturday names the companies.
6. Validate one assumption with our mentor or the sponsoring board member Saturday ("would your analyst use this weekly?") and put that quote in the video.
7. Lock the build Sunday by about 12:30; record the video and fill Devpost before 2:00.

## 9. Open questions for organizers
- Rubric criteria and weights?
- Video length limit? Is a live demo URL or repo required?
- Is pre-built scaffolding allowed beyond disclosure? Any AI tool or API restrictions?
- Pharma case: are the three companies and products specified? Any data beyond public 10-Ks? Can we talk to the sponsoring board member?
- Seven awards or ten? Per case or per track?
- How long is each judge visit, and how many judges per team? Is the video also scored?

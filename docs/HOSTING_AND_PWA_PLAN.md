# Hosted phone capture and model integration plan

Prepared 26 September 2026. This is an implementation plan; no cloud resources,
billing subscriptions, public endpoints or keep-alive monitors have been created.
The aim is a hosted phone camera experiment using the existing three-level model,
with reproducible results and access limited to the research team initially.

## Local implementation checkpoint — 26 September 2026

Hosting is deferred at the user's request. The local prototype now implements
camera capture/preview/retake, a PWA shell, explicit IndexedDB pending evidence,
SQLite book/image retention, saved-book navigation, operation receipts and
revision conflicts, OCR work reservations, page replacement history and reviewer
annotations in exports. Inference caches are bounded and the broad prediction is
reused when building the three-level path. See `prototype/README.md` for local
testing and exact limits.

This closes part of the local experiment work in milestones 1–3, rather than
declaring the deployment milestones complete. User authentication, multi-process
storage, cloud packaging/deployment, measured Linux memory/latency, representative
Indian-language book evaluation, long-text chunking and physical Android/iPad
tests are still separate work. Model weights and review thresholds are unchanged.

## Hosting decision

Use one portable Docker image for FastAPI, the PWA assets, Tesseract and the pinned
model artifacts. Prefer Google Cloud Run for a managed, low-traffic pilot if a
billing account is acceptable. Use Oracle Always Free Ampere as the alternative
when staying within a fixed free allocation is the priority and capacity is
available. An eligible Azure for Students subscription is another practical
academic route. Account eligibility and actual provisioning remain unverified.

| Option | Current offer and constraint | Decision for this project |
|---|---|---|
| Render Free | 0.1 CPU, 512 MB RAM | Poor fit for the current Python encoder/OCR stack. Consider only after a smaller runtime is independently demonstrated to fit. |
| Google Cloud Run | Monthly usage allowance; scales to zero; billing account required | Preferred managed pilot, with explicit cost controls and cold-start handling. Free within allowances, not guaranteed zero total cost. |
| Oracle Always Free Ampere | Current documentation describes 2 OCPUs and 12 GB total for Always Free tenancies | Enough nominal memory; requires VM administration, Arm-compatible dependencies and available capacity. Idle instances may be reclaimed. |
| Azure for Students | Eligible students receive $100 credit usable within 12 months without a credit card at signup | Useful academic pilot funding; credit is finite, not perpetual free hosting. |
| Hugging Face Docker Spaces | CPU Basic has no hourly charge, but creating compute Spaces now requires a paid plan | Do not assume a new Docker deployment is free. |

Sources checked on the plan date: [Render compute](https://render.com/docs/compute-plans),
[Cloud Run pricing](https://cloud.google.com/run/pricing),
[Google free-program requirements](https://docs.cloud.google.com/free/docs/free-cloud-features),
[Oracle resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[Azure student offer](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p),
[Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-overview).

### Current prices checked 26 September 2026

The following figures are the provider-published rates or allowances checked for
this plan. They are planning inputs, not a quote: regions, taxes, account status,
egress, logs, storage, builds and provider policy changes can alter the final
bill.

| Service | Current published offer | Fit for this project |
|---|---|---|
| Google Cloud Run | First 180,000 vCPU-seconds, 360,000 GiB-seconds and 2,000,000 requests/month are in the request-based free allowance. Standard rates are $0.000024/vCPU-second, $0.0000025/GiB-second and $0.40/million requests. | Best managed pilot. At 1 vCPU/2 GiB, 1,000 books × 3 requests × 5 billed seconds consumes 15,000 vCPU-seconds and 30,000 GiB-seconds, so the compute/request portion is within the allowance. An always-on 1 vCPU/2 GiB service would be about $76.21/month before other charges. |
| Oracle Always Free Ampere A1 | Up to 2 OCPUs and 12 GB RAM total, subject to the tenancy's monthly Always Free allocation and regional capacity. | Best permanent-free memory fit. The Mumbai home region currently reports no A1 capacity for the attempted shape; retry without a fault domain and with a smaller 1 OCPU/6 GB allocation. |
| Azure Container Apps | First 180,000 vCPU-seconds, 360,000 GiB-seconds and 2,000,000 requests/month per subscription are free. Azure for Students provides $100 credit for 12 months to eligible students. | Viable academic alternative to Cloud Run, subject to student eligibility and regional price validation. The credit is temporary. |
| IBM Cloud Code Engine | Free tier includes 100,000 vCPU-seconds, 200,000 GB-seconds and 100,000 HTTP requests/month. Applications can scale to zero. IBM’s separate Lite plans never expire, but Lite instances can sleep after 10 days without development activity and be deleted after 30 days. | Viable low-traffic managed pilot if a pay-as-you-go account and cost controls are acceptable. The free allowance is smaller than Cloud Run’s, and IBM Container Registry Free is limited to 500 MB image storage and 5 GB/month pull traffic. Our model image is likely to exceed 500 MB. |
| Railway | Free is $0 with $1/month credit and a 0.5 GB RAM, 1 vCPU, 1 replica cap. Hobby is $5/month including $5 resource usage. | Free is below the measured memory need. Hobby is a predictable small paid fallback, but profile the container before relying on it. |
| Koyeb | Free instance is 512 MB RAM and 0.1 vCPU. `eco-medium` (1 vCPU/2 GB) is listed at about $10.71/month; `medium` (2 vCPU/2 GB) about $21.43/month. | Free is too small. The paid 2 GB options are possible budget fallbacks, with regional and workload limits to verify. |
| Fly.io | No current permanent free compute tier. Published examples are about $15.55/month for shared 8x/2 GB and $31/month for performance 1x/2 GB, before volumes and egress. | Historical “3 free VMs” advice is stale. Use only if paying for a VM-like deployment is acceptable. |
| AWS Lightsail | Linux VM examples are $12/month for 2 GB and $24/month for 4 GB. The initial free trial is time-limited. | Predictable paid VM fallback; not a permanent free solution. |
| AWS EC2 | New accounts can receive up to $200 in credits, with the Free Plan ending after 6 months or when credits are exhausted. AWS marks `t3.small` (2 GiB) and `t4g.small` (2 GiB Arm) as eligible for the new offer; older accounts have the legacy 12-month micro-instance offer. | Suitable for a credit-funded pilot, especially if persistent VM administration is acceptable. It is not permanent free compute; EBS, public IPv4, data transfer and other resources need separate controls. |
| Render | Free is 0.1 CPU and 512 MB RAM, with sleep after 15 minutes idle and ephemeral local files. | Not suitable for the current stack. Keep-alive traffic does not increase memory or persistence. |
| Cloudflare Workers | Free allows 100,000 requests/day, 10 ms CPU/request and 128 MB per isolate. | Useful for a static PWA or thin proxy only; cannot run Python/Tesseract/E5 inference. |

At 1 vCPU/2 GiB, continuously active Cloud Run for a 730-hour month is
approximately `(2,628,000 × $0.000024) + (5,256,000 × $0.0000025) = $76.21`
before requests, networking, registry, logs and storage. A scale-to-zero service
used only for the sample workload is far below the published compute allowance,
but startup time and ancillary charges still need monitoring. Never use an
artificial keep-alive to disguise an always-on service; set budgets and alerts and
design the client for cold starts instead.

The linked GitHub comparison is useful for discovering candidates, but several of
its free-tier entries (especially Heroku and Fly.io's historical free VMs) are no
longer current. Treat the provider pricing pages above as the source of truth.

IBM’s free-account page describes Lite services as always free, but that does not
mean an unrestricted free VM or container. Code Engine is the IBM service to test
for this workload: it supports a 1 vCPU/2 GB application, scale-to-zero and
request-based billing. The sample workload above would consume 15,000 vCPU-seconds,
30,000 GB-seconds and 3,000 requests, below Code Engine’s published free amounts.
An always-on 1 vCPU/2 GB application would be approximately $104.74/month before
HTTP calls, image storage, pulls, logs and other services, using IBM’s published
example rates. [Code Engine pricing](https://cloud.ibm.com/docs/codeengine?topic=codeengine-pricing)
[IBM free account](https://www.ibm.com/cloud/free)
[Container Registry limits](https://cloud.ibm.com/docs/Registry?topic=Registry-registry_overview)

AWS should be treated similarly: its current Always Free offers are mostly
service-specific monthly allowances, not a permanently free general-purpose EC2
instance. For accounts opened on or after 15 July 2025, AWS provides $100 of
credits at signup and up to $100 more through qualifying activities; the Free Plan
ends after six months or when the credits are used. For older accounts, the legacy
EC2 offer is limited to 12 months. A `t3.small` has 2 GiB RAM and AWS lists it at
about $0.0209/hour in its published T3 example, roughly $15.26 for 730 hours
before EBS, IPv4, transfer and regional differences. A `t3.medium` with 4 GiB is
about $30.51/month at that example rate. [AWS Free Tier](https://aws.amazon.com/free/)
[EC2 Free Tier eligibility](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)
[T3 pricing](https://aws.amazon.com/ec2/instance-types/t3/)

A local sample run on macOS loaded the hierarchy model and processed
`prototype/samples/informative_back.png`. Python peak resident memory was
860,717,056 bytes (about 821 MiB); the separately reported child-process peak was
94,978,048 bytes (about 91 MiB). These peaks need not coincide. This is one small
synthetic image, not a Linux container limit or a high-resolution/concurrency
benchmark. It strongly argues against assuming the current stack fits 512 MB.
Measure actual container memory before selecting the final instance size.

### Render and continuous pings

Render sleeps an idle free service after 15 minutes; waking takes approximately
one minute. Its free allowance is 750 running instance-hours per workspace each
month. Inbound keep-alive traffic may delay idle sleep, but cannot prevent
platform restarts, increase memory, or make in-memory sessions durable. Free
local files are ephemeral. Build for restart and wake-up rather than relying on
continuous artificial traffic. [Render free-service behavior](https://render.com/docs/free)

### Cloud Run pilot settings and costs

Start the Linux profile at 1 vCPU, 2 GiB RAM, one worker, concurrency 1, minimum
instances 0, maximum instances 1, and request-based billing. These are proposed
settings, conditional on image-size stress tests; use a larger limit only after
reviewing the measured need and cost. Configure model threads to the allocated
CPU count. Serve frontend and API from the same origin initially to simplify
camera access, authentication and deployment.

Request-based free allowances are 180,000 vCPU-seconds, 360,000 GiB-seconds and
two million requests monthly, expressed using us-central1 pricing. For illustration,
1,000 books × 3 requests × 5 billed seconds at 1 vCPU/2 GiB would consume
15,000 vCPU-seconds and 30,000 GiB-seconds before startup/shutdown and other work.
Five seconds is an assumption, not a measured cloud latency. Region prices,
other projects and actual usage affect the allowance. [Pricing](https://cloud.google.com/run/pricing)

Use budget alerts and the Cloud Run spend-cap mechanism described in current
billing documentation, checking availability and enforcement behavior in the
chosen account. Inventory registry storage, builds, object storage, database,
network traffic and logs separately; a compute cap is not a universal zero-bill
guarantee. Avoid unnecessary networking components and retain only a small
number of image versions. Minimum instances remain zero; warm-up happens when
an operator starts a real experiment. [Billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings)

## Target application

Phone PWA communicates over HTTPS with an authenticated FastAPI service.
FastAPI verifies access, loads current book evidence, runs bounded OCR and the
hierarchy classifier, commits the updated state, and returns the next action.
A database stores sessions, capture revisions, model versions, actions and
reviewer labels. Private object storage holds explicitly retained captures.

Supabase Free is a candidate for managed authentication, Postgres and private
storage. Its current allowance includes a 500 MB database and 1 GB file storage;
projects can pause after a week of inactivity. This is a pilot-size service, not
an unrestricted photo archive. At 1 MB per page, 300 books × three pages already
approaches 900 MB before originals, retries and backups. Plan retention, exports,
quota alerts and recovery before collecting a large dataset.
[Supabase pricing](https://supabase.com/pricing)

Do not treat PWA installation as offline ML. The interface can cache its static
assets and retain pending captures locally; inference still requires the backend.
The app must say whether an image is pending, uploading, processing, failed or
complete. Do not cache private API responses in the service-worker asset cache.

### Role of an old iPad

An iPad 5th generation is a good low-cost capture and kiosk device. Apple lists an
A9 chip, 32 GB or 128 GB storage, an 8 MP rear camera and 802.11ac Wi-Fi for this
model. It can open the PWA, take book photos and upload them over the local network
or HTTPS. [Apple specifications](https://support.apple.com/en-my/111960)

It should not be the model server. The current backend uses FastAPI, Tesseract,
`sentence-transformers`, Transformers and PyTorch; a local run already reached
about 821 MiB Python resident memory. iPadOS does not provide a general-purpose
daemon model: background execution is limited to system-provided modes, and
third-party apps are suspended when their permitted background work ends. iSH can
provide a Linux-like shell, but it is a user-mode x86 environment intended for
interactive use, not a reliable always-on Python/Torch service. [Apple background
execution](https://developer.apple.com/documentation/Xcode/configuring-background-execution-modes),
[iSH](https://ish.app/)

Use the iPad as a thin client in the first experiment:

1. Open the hosted PWA or a local frontend on the iPad.
2. Capture and resize the page image in the browser.
3. Send it to the FastAPI service on Cloud Run, OCI, a Mac, a Raspberry Pi or an
   old laptop.
4. Display L1/L2/L3 results and the next-page request on the iPad.

For a fully local demonstration, place the backend on a laptop or small Linux
computer on the same Wi-Fi and let the iPad connect to its private IP. This gives
the desired “no public cloud” experiment while keeping inference on hardware that
can run the Python dependencies. Leaving the iPad connected to power is acceptable
for kiosk use if it stays ventilated and the battery is not swollen; prolonged
heat and full charge accelerate battery wear. [Apple battery guidance](https://support.apple.com/en-au/118418)

Jailbreaking would make a LAN daemon, SSH access or a watchdog more feasible, but
it does not make the iPad a suitable host for the current model. The official
palera1n project lists the iPad 5th generation among supported devices, with
support depending on the installed iPadOS version; its own documentation warns
about data-loss and recovery risks. A reboot can also require computer-assisted
re-jailbreaking, so it is a poor foundation for an unattended server. If the team
uses a spare, wiped iPad for experimentation, keep any jailbroken service on the
private LAN and use the iPad as a capture client or lightweight relay. [palera1n
support](https://github.com/palera1n/palera1n)

## Milestone 1 — Package and profile the runtime

- Create a minimal CPU Docker build and deployment-only dependency set, excluding
  notebooks, training data and PDF-building dependencies.
- Bundle the fixed encoder, hierarchy classifier and OCR packs with hashes and
  versions. Retrieve trusted private artifacts using build secrets or a private
  release mechanism; do not place credentials in image layers. No training on
  the serving host and no model download on the first camera request.
- Add readiness, liveness, structured timing and model-version reporting. Expose
  the configured port and origins without broadly disabling host checks.
- Bound the embedding cache, decoded image dimensions and transient OCR memory.
  Keep photos out of long-lived process dictionaries. Avoid loading multiple
  encoder copies through multiple workers.
- Profile cold start, small and high-resolution photos, contrast repair, long
  text, repeated requests and memory after session cleanup in Linux. Test the
  relevant CPU architecture before committing to an Arm VM.

Completion: reproducible image; existing model/OCR tests pass; no out-of-memory
failure at supported inputs; measured peak fits the chosen allocation with an
explicit headroom target of at least 25%.

## Milestone 2 — Authentication and durable experiment state

- Add invitation-based accounts and server-side ownership checks for every book,
  image, trace, repair and export. Test cross-user isolation.
- Replace global in-memory session state with a repository interface and database
  records. Store page replacements as revisions while only current usable
  evidence affects classification. Define deletion and retention behavior.
- Add per-session revision checks, operation IDs and idempotency keys so retries
  do not double-count OCR or overwrite newer captures. Record consumed OCR work
  even if classification or the final response fails.
- Move original images to private object storage with controlled access and keep
  ephemeral decoded buffers only for processing. Strip unnecessary location
  metadata from retained captures while retaining orientation correctly.
- Keep inference inside the request for the first low-traffic Cloud Run version;
  use bounded admission and retry responses. Do not launch untracked background
  work after a response on request-based compute. Durable asynchronous jobs can
  be introduced if measured latency warrants the extra service.

Completion: a process restart, lost response or duplicate upload preserves the
book state and accounting. Two simultaneous captures cannot corrupt one session.
Another account cannot retrieve its photos or results.

## Milestone 3 — Phone camera PWA

- Add an install manifest, icons, responsive camera screen and versioned asset
  caching. Provide Android and iPhone installation guidance appropriate to the
  browser. Preserve a normal-browser path if installation is unavailable.
- Add rear-camera preview, capture, retake and a file/camera-picker fallback.
  Handle permission denial, camera switching, orientation and leaving the page;
  stop camera tracks when capture closes. Reuse useful legacy camera code after
  testing it against the new API.
- Carry page type and OCR language through each capture and display class,
  division, section, support limitations and requested next evidence.
- Use an IndexedDB queue for explicit pending captures, with user-visible retry,
  cancel and deletion. Resume sync on reopening/foreground connectivity rather
  than assuming mobile background sync always runs.
- Measure resizing/compression effects on text recognition. Retain capture and
  processing dimensions; do not reuse pixel-height thresholds across arbitrary
  scaling without evaluation. Keep permitted reference originals for the study.
- Show waking, uploading and processing as distinct states. Retry with backoff
  and idempotency keys; preserve the capture while the backend wakes.

Completion: real Android Chrome and iPhone Safari tests cover camera permission,
portrait/landscape, install, retake, interrupted connection, retry and restart.
Desktop emulation alone does not close this milestone.

## Milestone 4 — Integrate and deploy the pilot

- Use the newer capture prototype as the primary application. Publish a stable
  three-level API contract, then migrate useful legacy capture/review features.
  Keep optional cloud classification disabled unless explicitly selected; do not
  expose incompatible broad-only legacy responses as hierarchy results.
- Parameterize app URLs, authentication and storage. Keep secrets server-side.
  Change text such as “images stay on this machine” to accurately explain hosted
  processing and retention.
- Deploy an access-controlled HTTPS endpoint on the chosen provider. Validate
  cold-start recovery, model hashes, accounts, storage and representative phone
  captures. Set quotas, usage controls, logs and backup/export procedures.
- Add CI for model/routing tests, API contracts, frontend checks and the container
  build. Use versioned releases and a documented rollback. Keep protected model
  artifacts separate from ordinary public build output.

Completion: the team can run the entire phone flow without the laptop being on;
restart recovery and access isolation pass; no unreviewed public demo is required.

## Milestone 5 — Collect evidence and improve classification

- Select the library's most important divisions/sections and target languages.
  Start with Hindi and Marathi alongside English unless the team prioritizes
  others; include Tamil if recruiting sufficient reviewers and books.
- Record book/work/edition identifiers, verified L1/L2/L3 labels, language, page
  type, transcription, reviewer, label source and capture defects. Resolve
  ambiguous catalog labels with librarians instead of selecting the first code.
- Obtain an initial field pilot across languages, devices and capture defects.
  Use it for engineering and threshold development, not final accuracy claims.
  Size the independent test set around coverage and uncertainty requirements.
- Keep editions, translations and all photos of a work in one split. Freeze the
  final evaluation set before selecting models or thresholds.
- Implement page-aware chunking with traceable evidence and compare aggregation
  approaches on development data. This addresses the current 512-token limit.
- Compare the current conditional hierarchy with joint section ranking and a
  retrieval-assisted candidate list backed by a permitted, reviewed catalog.
  Compare native-script and translation-assisted approaches on the same groups.
  Fine-tune only when sufficient reviewed training data exists.
- Evaluate quantized/ONNX inference for deployment efficiency as a separate
  experiment. Check accuracy, calibration, memory and CPU; do not promise a
  512 MB deployment merely from smaller weight files.
- Add reviewer corrections as auditable annotations. Retraining is a versioned
  reviewed process, not an automatic update from every correction.

Completion: per-language and per-level accuracy, macro-F1, selective coverage,
calibration and unseen/rare-section behavior are reported; new model promotion
requires an explicit development-set criterion and regression checks.

## Milestone 6 — Controlled capture experiment and technical disclosure

- Compare cover-only, all available pages, retry-first and adaptive policies on
  the same reviewed books. Replay a fixed image collection for controlled
  algorithm comparisons; separately run a counterbalanced phone usability study
  to measure actual recapture and operator effort.
- Include quality-only, uncertainty-only and model-support-aware variants.
  Record every processed image, page revision, rule version and model version.
- Measure L1/L2/L3 performance, OCR character/word error, useful page requests,
  retries, pixels processed, bytes uploaded, review rate and completion rate.
  Report OCR, inference, network and cold-start latency separately.
- Select thresholds on development books, then compare processing cost at
  matched classification quality or review coverage on a locked test set.
  Use book-level uncertainty intervals rather than treating pages as independent.
- Update the technical disclosure, diagrams and demonstrated examples to match
  what was actually deployed and measured. Record inventor contributions and
  preserve dated versions for the university IPR review. PWA packaging itself
  is not evidence of novelty, and efficiency gains remain unproven until tested.

Completion: reproducible evaluation tables and ablations, traceable examples,
limitations, and an updated technical package for the IPR cell.

## Order and decisions

Execute milestones 1–4 before the live field experiment. Milestone 5's label
review and recruitment can proceed during deployment work; its model experiments
and milestone 6 follow usable data collection. Real-phone tests and reviewer
availability determine the schedule more than creating the manifest.

Before provisioning, confirm provider account availability, whether a billing
account is acceptable, the allowed spend ceiling and initial testers. These do
not block preparing the Docker build, storage schema or PWA code. Actual accounts,
resource creation and any paid subscription remain separate deployment steps.

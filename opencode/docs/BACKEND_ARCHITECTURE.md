\# Backend Architecture



\## Framework



FastAPI



Base prefix:



/api



Admin routes:



/api/admin



\---



\## Routers



core.py



Authentication

Subjects

Topics



\---



practice.py



Questions

PYQs

Attempts

Notes

Flags

Mistakes



\---



playlists.py



YouTube playlist import

Video progress



\---



resources.py



Google Drive OAuth

Drive sync

Resources

Resource notes



\---



analytics.py



Dashboard

Subject analytics



\---



admin\_staging.py



PDF imports

Import jobs

Staging queue

Approval flow



\---



\## Authentication



Google OAuth login.



Development login exists:



POST /auth/dev-login



Sessions stored in:



user\_sessions



Cookie:



session\_token



\---



\## Storage



MongoDB



All collections accessed through Motor.



\---



\## Main Collections



users



user\_sessions



subjects



topics



questions



question\_attempts



question\_notes



question\_flags



pyqs



pyq\_attempts



pyq\_flags



mistakes



playlists



videos



video\_progress



resources



resource\_notes



drive\_credentials



staging\_questions



import\_jobs



\---



\## Question Flow



Question

&#x20;↓

Attempt

&#x20;↓

Stats

&#x20;↓

Analytics



\---



\## PYQ Flow



PYQ

&#x20;↓

Attempt

&#x20;↓

Stats

&#x20;↓

Analytics



\---



\## Playlist Flow



YouTube Playlist URL

&#x20;↓

YouTube API

&#x20;↓

Playlist

&#x20;↓

Videos

&#x20;↓

Video Progress



\---



\## Resource Flow



Google Drive

&#x20;↓

Drive Sync

&#x20;↓

Resources Collection



\---



\## Import Flow



PDF

&#x20;↓

Import Job

&#x20;↓

Parser

&#x20;↓

Staging

&#x20;↓

Approval

&#x20;↓

Questions / PYQs


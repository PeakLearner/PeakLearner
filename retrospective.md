It's been about 5 and a half months since I was hired at [Ezoic](https://www.ezoic.com/) and 3 months since I moved to San Marcos, CA.
This has given me time to both learn and reflect on where this project currently is, where it should be, as well as where I came up short.

The current state of the project isn't that far from succeeding. 
A lot of the core business logic is written out for labels, models, model summaries, and jobs.
The hardware is in place to allow for a lot of processing as well.
I stand by this being an ambitious but doable project.

This project comes short on devops by the biggest margin of anything. 
The issue with devops is that it is incredibly hard to know how to build a good pipeline/developer ecosphere that would work for a system like this. 
The world of kubernetes and deploying architecture would provide seamless deployments with more security, stability, and ease of use.
Yes, all of this could be built once and put in place but it would take less time to do it the right way, as well as allow those working on the system to fail faster and learn faster, as well as revert things easier when necessary.
Routing connections to different test servers configured to different web addresses would be easy to set up without requiring as much configuration knowledge.

[First principles design](https://www.element84.com/blog/designing-from-first-principles) says to question the requirements and not having an sql database in favor of berkeleydb was one that caused me to get stuck.
It could still have a place in the application but using it as the primary database was always going to be prone to failure. 
Yes, it could work but the amount of effort to make it do the right thing has already been done by other people, no need to reinvent the wheel.

Maybe this is a "better ask for forgiveness than permission" thing that I was missing before, but I could have leveraged the schools better by installing this stuff myself.
I was extremely hesitant to mess hardware outside my control up or do something that could anger IT/lose my job. 

I fell short in experience. 
The more experience I have gathered working with other software engineers as well as on code that I didn't write, the more confident I feel in asking the right questions as well as questioning the right things.
Another place I felt short is prioritizing the right things. There are still 8 issues open of varying severity/impact, and I always felt like these were "looming" over my shoulder.

Another thing I ran into a lot is the [GIL or python global interpreter lock](https://realpython.com/python-gil/).
A langauge like golang (the one my company uses) or rust would be better suited for this application (at least the backend part).
Python is a great language for proof of concept work but heavy lifting code such as this needs to be a compiled language with many instances of that deployed vs one version in a docker image.

The new version of jbrowse should be substantially easier to develop for and utilize all the new advancements from modern frontend frameworks.

Breaking up the code and deploying everything separately would be an instant improvement as well.
Deploying everything separately and utilizing a good devops pipeline has shown me the light.

At the end of the day, I still think about this project a lot and how it could be improved by what I have learned.

This is probably super unorganized, but I've been meaning to write this for a long time, but now I feel like I have something to say.
The amount of personal growth I had during the research is something I will be forever grateful for. 
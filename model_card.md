## Model Name

Music Matcher+

## Intended Use

The recommender is designed to prioritized genre and energy to find the perfect songs for the user. It is for people who prefer to find songs they would like in specific genres rather than songs that have similar vibes.

## Limitations and Biases

Some limitations is that you cant search for specific artists. For example if a user wanted to find new artist and not particular songs that is not something it can do. Another limitation is that sometimes it can get genre's wrong. When searching certain songs it will pull the wrong genre and the confidence level when recommending songs will drop below 50%.

## Misuse

I don't believe that their is any way you can misuse this AI. It is a simple recommendation system that uses Gemini to generate explanations. The only way I can see users exploiting this is by running the generation many times over to try to break the generation.

## Reliability 

The recommender is pretty reliable with the recommendations being to my expectations 7/8 of the times I tested it. Most times the pipeline was able to correctly match genre to the song and give accurate recommendations.However, on the time it got it wrong in the explanations the confidence score it gave each recommendation were very low i.e(.50, .25). This lets me know that even when it does get the genre wrong it does not have blind confidence in its recommendations. 

## Collaborations 

One good suggestion the system came up with was the overall pipeline and feedback function. At first I didn't know how exactly I wanted to extend the project so I gave the agent a general prompt and it built out the prototype version of the site that gave me a good idea of where I wanted to go next. One bad suggestion was when I was trying to get it to build out the search bar I prompted it to detect genre from the song in the search. When it began planning in the plan it discussed creating a detect genre button for the song in the search bar which was not what I was looking for at all. To fix this issue I abandoned that plan and told it that what I was looking for was something that would autodetect the genre from the song in the search and use that to match songs for recommendation rather than a tool that just detects genre. After this it spun up a plan that was more in line with what I was looking for and I accepted it.
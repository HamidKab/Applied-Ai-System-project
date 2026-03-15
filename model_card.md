# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  
MusicMind

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

The recommender is designed to prioritized genre and energy to find the perfect songs for the user. It is for people who prefer to find songs they would like in specific genres rather than songs that have similar vibes.
---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

---
The way my scoring works is that it prefers genre overall. If the song and user favorite genre has a match it gives a score of +.50. It gives other objects such as mood and energy a score of +.25 and .20 respectively. This is so that even if a song has a higher mood and energy score it does not go over a genre match.


## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---
The data set is 23 songs long. Originally I believe the data set was only 5-10 songs long and was missing important genres such as hip-hop and jazz. I added these genres to the dataset as well as other songs to have a more rounded source of data.

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

---
It gave good scores off the bat to the default user pref which consisted of pop music. I believe in this case the Recommender system matched my intuition of what I think that user would have liked.
## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

---
Intially it had a hard time scoring users that preferred hiphop. It showed preference to mood and energy over genre. It also sometimes couldn't recognize the genre due to spelling or what have you. In these cases it would overfit to pop.

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

---
After making changes to the recommender system i believe it performs more as expected. I increased the score giving to a genre match so that genre would hold more weight and added a system to match different spellings of hiphop so that it would catch it. To confirm this i tested user_pref_3 to see if the recommendations matched my intuition.
## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---
In the future maybe allowing for more nuance in the recommender. Right now it recommends based on genre straight up but that lacks nuance. Their exist so many different sub-genres of music that the csv and the model dont really capture. If i were to improve it i'd map sub genres in the user preference and add to the score depending on how many genre matches exist.

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
I learned a lot about model training and optimizing. At first the idea of model training seemed like an impossible task but the more i worked on this project the less daunting it seemed. This project gave me insight on how recommendation models work and allowed me to start training my own models outside of this.
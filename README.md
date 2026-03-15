# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Explain your design in plain language.

Some prompts to answer:

- What features does each `Song` use in your system
  - For example: genre, mood, energy, tempo
- What information does your `UserProfile` store
- How does your `Recommender` compute a score for each song
- How do you choose which songs to recommend

You can include a simple diagram or bullet list if helpful.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this




---

## 7. `model_card_template.md`

Combines reflection and model card framing from the Module 3 guidance. :contentReference[oaicite:2]{index=2}  

```markdown
# 🎧 Model Card - Music Recommender Simulation

## 1. Model Name

Give your recommender a name, for example:

> VibeFinder 1.0

---

## 2. Intended Use

- What is this system trying to do
- Who is it for

Example:

> This model suggests 3 to 5 songs from a small catalog based on a user's preferred genre, mood, and energy level. It is for classroom exploration only, not for real users.

---

## 3. How It Works (Short Explanation)

Describe your scoring logic in plain language.

- What features of each song does it consider
- What information about the user does it use
- How does it turn those into a number

Try to avoid code in this section, treat it like an explanation to a non programmer.

I learned that most recommenders like spotify or netflix use a hybrid recommender systems. This means they collect data like plays skips and likes and generate candidate items. They rank the candidates and output recommendations. My recommendation system works similarily prioritizing genre, mood, and energy.

In my system if the genre matches the users favorite genre its a +.35 and if it matches their favorite mood +.25 it then measures the closeness_score to get a energy match it then returns the overall score
flowchart TD
    A[Start] --> B[Load Songs Data]
    B --> C[Create UserProfile]
    C --> D[For each Song]

    D --> E{Genre matches favorite_genre?}
    E -- Yes --> E1[+0.35]
    E -- No --> E2[+0.00]

    E1 --> F{Mood matches favorite_mood?}
    E2 --> F
    F -- Yes --> F1[+0.25]
    F -- No --> F2[+0.00]

    F1 --> G[Compute energy_match = closeness_score(song.energy, target_energy)]
    F2 --> G
    G --> G1[+0.30 * energy_match]

    G1 --> H[Set preferred_acoustic = 1.0 if likes_acoustic else 0.0]
    H --> I[Compute acoustic_match = closeness_score(song.acousticness, preferred_acoustic)]
    I --> I1[+0.10 * acoustic_match]

    I1 --> J[Total score for song]
    J --> K{More songs?}
    K -- Yes --> D
    K -- No --> L[Sort songs by score descending]
    L --> M[Return top-k recommendations]

    M --> N[Optional: explain_recommendation]
    N --> O[Build reasons: genre/mood match + energy similarity + acoustic fit]
    O --> P[End]

    subgraph Closeness Score
      CS1[feature_range = max_value - min_value]
      CS2{feature_range <= 0?}
      CS3[Return 0.0]
      CS4[normalized_distance = |value - target| / feature_range]
      CS5[Return max(0.0, 1.0 - normalized_distance)]

      CS1 --> CS2
      CS2 -- Yes --> CS3
      CS2 -- No --> CS4 --> CS5
    end

---

## 4. Data

Describe your dataset.

- How many songs are in `data/songs.csv`
- Did you add or remove any songs
- What kinds of genres or moods are represented
- Whose taste does this data mostly reflect

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

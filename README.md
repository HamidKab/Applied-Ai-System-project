## Applied AI System

## Original Project

The original project was the ai110-module3show-musicrecommendersimulation-starter.
The original purpose of this project was to build a trained music recommender model that could represent songs and a user "taste profile" as data and, using a scoring rule, turns that data into recommendations. The system recommends based on genre, mood, energy, tempo. The user profile consist of the preferences of genre, mood, energy, and if they like acoustics or not. The recommender should prefer genres and score it higher than other aspects. If the recommender finds a match for between a songs values and user preferences it favors those songs. If a song has a similar genre preference to a user it will be preferred rather than songs that matches a users mood and energy but doesn't match genres.

## MusicMatcher+

## Title and Summary
My project is called MusicMatcher+. It is an extension of the music recommender project we had worked on previously. It is a human in the loop recommender system that takes user preferences as an input and outputs recommendations based on how closely they match the users preferences. It then uses gemini's API to generate a explanation of the recommendation. It then allows users to validate the recommendation and leave feedback to help improve the recommender.


## Architecture Overview

flowchart TD
    A["👤 User Input<br/>Genre, Mood, Energy, Acoustic Pref"] -->|Human validates input| B["Input Validation<br/>(Check for invalid genres, etc.)"]
    
    B -->|✓ Valid| C["Retrieve Candidate Songs<br/>(Score > threshold)"]
    B -->|✗ Invalid| B1["🧑‍💼 Human Review<br/>Clarify ambiguous input"]
    B1 --> B
    
    C --> D["Retrieve External Data<br/>Artist Info, Lyrics, Trending Data,<br/>User Reviews"]
    
    D --> E["🧪 Quality Check<br/>Verify retrieved data<br/>accuracy & relevance"]
    E -->|Issues found| E1["🧑‍💼 Human Review<br/>Curate/fix external data"]
    E1 --> D
    E -->|✓ Quality OK| F
    
    F["Augment Song Metadata<br/>Enrich with retrieved info"]
    F --> G["Generate Explanations<br/>LLM: Why this song matches user"]
    
    G --> H["🧪 Explanation Validation<br/>Check for:<br/>- Hallucinations<br/>- Factual accuracy<br/>- Relevance"]
    H -->|Issues| H1["🧑‍💼 Human Review<br/>Refine prompt/generation rules"]
    H1 --> G
    H -->|✓ Valid| I
    
    I["Rank Recommendations<br/>By score + explanation quality"]
    I --> J["🧪 Bias & Fairness Check<br/>Genre representation<br/>Artist diversity<br/>Mood balance"]
    J -->|Bias detected| J1["🧑‍💼 Human Review<br/>Adjust weights/filters"]
    J1 --> I
    J -->|✓ Fair| K
    
    K["Return Top-k<br/>Recommendations with<br/>Enhanced Explanations"]
    K --> L["👤 User Receives<br/>Ranked Song List +<br/>AI-Generated Reasons"]
    
    L --> M["🧪 User Feedback Loop<br/>Did you like these?<br/>Was the explanation helpful?"]
    M --> N["🧑‍💼 Human Analysis<br/>Assess model performance<br/>Identify failure patterns"]
    N -->|Systematic issues| O["Model Refinement<br/>Update weights, prompts,<br/>retrieval sources"]
    O --> D
    N -->|Edge cases| P["Test Dataset<br/>Store for regression testing"]
    
    style A fill:#e1f5ff
    style L fill:#e1f5ff
    style B fill:#fff3e0
    style E fill:#f3e5f5
    style H fill:#f3e5f5
    style J fill:#f3e5f5
    style M fill:#c8e6c9
    style B1 fill:#ffe0b2
    style E1 fill:#e1bee7
    style H1 fill:#e1bee7
    style J1 fill:#e1bee7
    style N fill:#a5d6a7
    style O fill:#f0f4c3

The pipeline starts with the user inputting their preference. It then validates whether or not the inputs were valid. After validating the inputs it retrieves candidate songs. It then allows users to do a quality check on the recommendations I.e. were the recommendations what the user expected/wanted. If the user is ok with the retrieved songs the pipeline will then generate an explanation of why each song was recommended. THe user can then validate the explanations, check for hallucinations, accuracy, or relevance. After all that the top k songs are returned with the explanations and the user can give feedback.

## Set up instructions

Run:

python -m venv .venv

Install required packages:

pip install -r requirements.txt

Create a .env file in the project root.

Add:

GEMINI_API_KEY=your_api_key_here

streamlit run app.py

## Design Decisions

I designed the the recommender to be more a human in the loop system rather than an automated ranker. The recommendation model by default prioritizes genre because I believe genre matches

## Testing Summary

## Reflection
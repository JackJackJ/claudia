# Thanks for checking out Claudia!

Claudia is a very lightweight Discord bot that takes listens to user queries and responds in the server. Claudia has the capacity to remember previous conversations as well as the personality of server members, and will adapt as they learn more about you and your friends.

## How to set up Claudia
This will require some slight editing of the source code.

 - Obtain your API key from the Anthropic website (support for Gemini and ChatGPT coming soon)
 - Obtain your Discord bot token from the Discord developer portal
 - Copy and paste these into the API key section and the token section at the top of Claudia.py
 - If you wish, you may add a system prompt for Claudia (something that tells Claudia who they are). This is located in (currently) line 119, simply edit the system field to whatever role you wish Claudia to play in your server, For example: "You are Claudia, a helpful robot assistant."
 - Keep in mind Claudia runs on Sonnet 3.5 by default, which is quite expensive. You can change the model to a more affordable version of Claude in the source code. 
 - After that, you're all set! Run the script in the environment of your choice.
## Have fun chatting!

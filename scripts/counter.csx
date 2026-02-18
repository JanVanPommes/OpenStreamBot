using System;
using System.IO;

// Name of your variable (this will be used as %test% in the bot)
string varName = "test";

// We use a simple text file for persistence
// This file will be created in the current working directory of the bot
string fileName = $"counter_{varName}.txt";
int count = 0;

// 1. Read existing value if file exists
if (File.Exists(fileName)) 
{
    // Try to parse the content of the file as an integer
    int.TryParse(File.ReadAllText(fileName), out count);
}

// 2. Increment the counter
count++;

// 3. Save the new value back to the file
File.WriteAllText(fileName, count.ToString());

// 4. Send back to Bot
// The bot listens for lines starting with "SetVar:"
// This allows you to use %test% in subsequent actions (like Chat Message)
Console.WriteLine($"SetVar: {varName}={count}");

// Optional: Print to console for debugging (visible in bot logs)
Console.WriteLine($"Counter incremented to {count}");

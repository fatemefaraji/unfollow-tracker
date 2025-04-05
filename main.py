import requests
import json
import time
import os
from datetime import datetime

class GitHubTracker:
    def __init__(self, username, token=None):
        # Save the username we're tracking
        self.username = username
        self.headers = {}
        
        # Use token for higher API limits if provided
        if token:
            self.headers = {'Authorization': f'token {token}'}
        
        # File names for storing data
        self.dataFile = f"{username}_followers_data.json"
        self.followersFile = f"{username}_followers.json"
        self.historyFile = f"{username}_history.json"
        
        # Make sure our files exist
        self.initializeDataFiles()
    
    def initializeDataFiles(self):
        # Create files if they don't exist yet
        if not os.path.exists(self.followersFile):
            with open(self.followersFile, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.historyFile):
            with open(self.historyFile, 'w') as f:
                json.dump({
                    "newFollowers": [],
                    "unfollowers": []
                }, f)
                
    def getFollowers(self):
        # Grab all followers from GitHub API
        followers = []
        page = 1
        
        # Loop through paginated results
        while True:
            url = f"https://api.github.com/users/{self.username}/followers?page={page}&per_page=100"
            response = requests.get(url, headers=self.headers)
            
            # Handle errors
            if response.status_code != 200:
                print(f"Oops! Error getting followers: {response.status_code}")
                return []
            
            pageFollowers = response.json()
            # Break if no more followers
            if not pageFollowers:
                break
                
            # Add follower info to our list
            followers.extend([{
                'login': user['login'],
                'id': user['id'],
                'avatarUrl': user['avatar_url'],
                'htmlUrl': user['html_url']
            } for user in pageFollowers])
            
            # Next page
            page += 1
            # Don't hit GitHub's rate limits
            time.sleep(1)
        
        return followers
    
    def saveCurrentFollowers(self, followers):
        # Save followers to file
        with open(self.followersFile, 'w') as f:
            json.dump(followers, f, indent=2)
    
    def loadPreviousFollowers(self):
        # Load the last saved follower list
        try:
            with open(self.followersFile, 'r') as f:
                return json.load(f)
        except:
            # Return empty list if file doesn't exist or is corrupt
            return []
    
    def updateHistory(self, newFollowers, unfollowers):
        # Add new events to our history log
        try:
            with open(self.historyFile, 'r') as f:
                history = json.load(f)
        except:
            # Start fresh if history file is missing or corrupt
            history = {"newFollowers": [], "unfollowers": []}
        
        # Add timestamp to each event
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Record new followers
        for follower in newFollowers:
            history["newFollowers"].append({
                "user": follower,
                "timestamp": timestamp
            })
        
        # Record unfollowers
        for unfollower in unfollowers:
            history["unfollowers"].append({
                "user": unfollower,
                "timestamp": timestamp
            })
        
        # Save updated history
        with open(self.historyFile, 'w') as f:
            json.dump(history, f, indent=2)
    
    def checkChanges(self):
        # The main function - check who followed and unfollowed
        currentFollowers = self.getFollowers()
        previousFollowers = self.loadPreviousFollowers()
        
        # Get just the usernames for easy comparison
        currentUsernames = [user['login'] for user in currentFollowers]
        previousUsernames = [user['login'] for user in previousFollowers]
        
        # Figure out who's new and who left
        newFollowers = [user for user in currentFollowers if user['login'] not in previousUsernames]
        unfollowers = [user for user in previousFollowers if user['login'] not in currentUsernames]
        
        # Save everything
        self.saveCurrentFollowers(currentFollowers)
        self.updateHistory(newFollowers, unfollowers)
        
        # Return what changed
        return {
            "newFollowers": newFollowers,
            "unfollowers": unfollowers,
            "totalFollowers": len(currentFollowers)
        }
    
    def getStats(self):
        # Get some cool stats about followers
        try:
            with open(self.historyFile, 'r') as f:
                history = json.load(f)
                
            currentFollowers = self.loadPreviousFollowers()
            
            # Return useful metrics
            return {
                "totalFollowers": len(currentFollowers),
                "totalNewFollowers": len(history["newFollowers"]),
                "totalUnfollowers": len(history["unfollowers"]),
                "recentNewFollowers": history["newFollowers"][-5:] if history["newFollowers"] else [],
                "recentUnfollowers": history["unfollowers"][-5:] if history["unfollowers"] else []
            }
        except:
            # Return zeros if something goes wrong
            return {
                "totalFollowers": 0,
                "totalNewFollowers": 0,
                "totalUnfollowers": 0,
                "recentNewFollowers": [],
                "recentUnfollowers": []
            }

# Demo code to show how to use this
if __name__ == "__main__":
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Track GitHub followers/unfollowers')
    parser.add_argument('username', help='Your GitHub username')
    parser.add_argument('--token', help='GitHub token for higher API limits')
    parser.add_argument('--check', action='store_true', help='Check who followed/unfollowed')
    parser.add_argument('--stats', action='store_true', help='Show your follower stats')
    
    args = parser.parse_args()
    
    # Create our tracker
    tracker = GitHubTracker(args.username, args.token)
    
    if args.check:
        print("Looking for changes...")
        changes = tracker.checkChanges()
        
        # Show new followers
        if changes["newFollowers"]:
            print(f"\n🎉 New Followers ({len(changes['newFollowers'])}):")
            for follower in changes["newFollowers"]:
                print(f"  • {follower['login']} - {follower['htmlUrl']}")
        else:
            print("\nNo new followers this time.")
            
        # Show unfollowers
        if changes["unfollowers"]:
            print(f"\n👋 Unfollowers ({len(changes['unfollowers'])}):")
            for unfollower in changes["unfollowers"]:
                print(f"  • {unfollower['login']} - {unfollower['htmlUrl']}")
        else:
            print("\nNobody unfollowed you. Nice!")
            
        print(f"\nYou have {changes['totalFollowers']} total followers")
        
    elif args.stats:
        # Show statistics
        stats = tracker.getStats()
        print(f"\n📊 Follower Stats for {args.username}:")
        print(f"  • Total Followers: {stats['totalFollowers']}")
        print(f"  • New Followers Ever: {stats['totalNewFollowers']}")
        print(f"  • Unfollowers Ever: {stats['totalUnfollowers']}")
        
        # Show recent new followers
        if stats['recentNewFollowers']:
            print("\n🆕 Recent New Followers:")
            for follower in stats['recentNewFollowers']:
                print(f"  • {follower['user']['login']} - {follower['timestamp']}")
                
        # Show recent unfollowers
        if stats['recentUnfollowers']:
            print("\n🔄 Recent Unfollowers:")
            for unfollower in stats['recentUnfollowers']:
                print(f"  • {unfollower['user']['login']} - {unfollower['timestamp']}")
    else:
        print("Hey! You need to use --check or --stats")
        print("Example: python script.py yourname --check")

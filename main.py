import requests
import json
import time
import os
from datetime import datetime
import logging

class GitHubTracker:
    """A class to track GitHub followers and unfollowers."""
    
    def __init__(self, username, token=None):
        """Initialize the tracker with a GitHub username and optional token.
        
        Args:
            username (str): The GitHub username to track.
            token (str, optional): GitHub personal access token for higher API limits.
        
        Raises:
            ValueError: If username is empty or not a string.
        """
        if not username or not isinstance(username, str):
            raise ValueError("Username must be a non-empty string")
        if token and not (isinstance(token, str) and len(token) >= 40):
            logging.warning("Token format looks invalid. Expected a 40-character string.")
        
        self.username = username
        self.headers = {'Authorization': f'token {token}'} if token else {}
        self.followersFile = f"{username}_followers.json"
        self.historyFile = f"{username}_history.json"
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, filename=f"{username}_tracker.log",
                          format="%(asctime)s - %(levelname)s - %(message)s")
        
        self.initializeDataFiles()
    
    def initializeDataFiles(self):
        """Create data files if they don't exist."""
        if not os.path.exists(self.followersFile):
            with open(self.followersFile, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.historyFile):
            with open(self.historyFile, 'w') as f:
                json.dump({"newFollowers": [], "unfollowers": []}, f)
    
    def check_rate_limit(self, response):
        """Check GitHub API rate limits and sleep if necessary."""
        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
        if remaining < 10:
            sleep_time = reset_time - time.time() + 1
            if sleep_time > 0:
                logging.info(f"Rate limit low ({remaining} remaining), sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)
    
    def getFollowers(self):
        """Fetch all followers from GitHub API.
        
        Returns:
            list: List of follower dictionaries with login, id, avatar_url, and html_url.
        """
        followers = []
        page = 1
        
        while True:
            url = f"https://api.github.com/users/{self.username}/followers?page={page}&per_page=100"
            response = requests.get(url, headers=self.headers)
            
            self.check_rate_limit(response)
            
            if response.status_code != 200:
                if response.status_code == 403:
                    logging.error("Rate limit exceeded. Try using a token or waiting.")
                elif response.status_code == 401:
                    logging.error("Invalid token. Please check your GitHub token.")
                else:
                    logging.error(f"Error getting followers: {response.status_code} - {response.text}")
                return []
            
            pageFollowers = response.json()
            if not pageFollowers:
                break
                
            followers.extend([{
                'login': user['login'],
                'id': user['id'],
                'avatarUrl': user['avatar_url'],
                'htmlUrl': user['html_url']
            } for user in pageFollowers])
            
            page += 1
            time.sleep(1)
        
        logging.info(f"Fetched {len(followers)} followers for {self.username}")
        return followers
    
    def saveCurrentFollowers(self, followers):
        """Save current followers to file."""
        with open(self.followersFile, 'w') as f:
            json.dump(followers, f, indent=2)
    
    def loadPreviousFollowers(self):
        """Load previously saved followers.
        
        Returns:
            list: List of follower dictionaries or empty list if file is missing/empty.
        """
        try:
            if os.path.getsize(self.followersFile) == 0:
                return []
            with open(self.followersFile, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def updateHistory(self, newFollowers, unfollowers):
        """Update history file with new followers and unfollowers."""
        try:
            with open(self.historyFile, 'r') as f:
                history = json.load(f) if os.path.getsize(self.historyFile) > 0 else {
                    "newFollowers": [], "unfollowers": []
                }
        except (json.JSONDecodeError, FileNotFoundError):
            history = {"newFollowers": [], "unfollowers": []}
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        max_history = 1000
        
        history["newFollowers"].extend([{"user": f, "timestamp": timestamp} for f in newFollowers])
        history["unfollowers"].extend([{"user": f, "timestamp": timestamp} for f in unfollowers])
        
        history["newFollowers"] = history["newFollowers"][-max_history:]
        history["unfollowers"] = history["unfollowers"][-max_history:]
        
        with open(self.historyFile, 'w') as f:
            json.dump(history, f, indent=2)
    
    def checkChanges(self):
        """Check for new followers and unfollowers.
        
        Returns:
            dict: Contains newFollowers, unfollowers, and totalFollowers.
        """
        logging.info(f"Checking changes for {self.username}")
        currentFollowers = self.getFollowers()
        previousFollowers = self.loadPreviousFollowers()
        
        currentUsernames = [user['login'] for user in currentFollowers]
        previousUsernames = [user['login'] for user in previousFollowers]
        
        newFollowers = [user for user in currentFollowers if user['login'] not in previousUsernames]
        unfollowers = [user for user in previousFollowers if user['login'] not in currentUsernames]
        
        self.saveCurrentFollowers(currentFollowers)
        self.updateHistory(newFollowers, unfollowers)
        
        return {
            "newFollowers": newFollowers,
            "unfollowers": unfollowers,
            "totalFollowers": len(currentFollowers)
        }
    
    def getStats(self):
        """Get follower statistics.
        
        Returns:
            dict: Contains totalFollowers, totalNewFollowers, totalUnfollowers,
                  recentNewFollowers, and recentUnfollowers.
        """
        try:
            with open(self.historyFile, 'r') as f:
                history = json.load(f) if os.path.getsize(self.historyFile) > 0 else {
                    "newFollowers": [], "unfollowers": []
                }
                
            currentFollowers = self.loadPreviousFollowers()
            
            return {
                "totalFollowers": len(currentFollowers),
                "totalNewFollowers": len(history["newFollowers"]),
                "totalUnfollowers": len(history["unfollowers"]),
                "recentNewFollowers": history["newFollowers"][-5:],
                "recentUnfollowers": history["unfollowers"][-5:]
            }
        except (json.JSONDecodeError, FileNotFoundError):
            return {
                "totalFollowers": 0,
                "totalNewFollowers": 0,
                "totalUnfollowers": 0,
                "recentNewFollowers": [],
                "recentUnfollowers": []
            }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Track GitHub followers/unfollowers')
    parser.add_argument('username', help='Your GitHub username')
    parser.add_argument('--token', help='GitHub token for higher API limits')
    parser.add_argument('--check', action='store_true', help='Check who followed/unfollowed')
    parser.add_argument('--stats', action='store_true', help='Show your follower stats')
    
    args = parser.parse_args()
    
    tracker = GitHubTracker(args.username, args.token)
    
    if args.check:
        print("Looking for changes...")
        changes = tracker.checkChanges()
        
        if changes["newFollowers"]:
            print(f"\n🎉 New Followers ({len(changes['newFollowers'])}):")
            for follower in changes["newFollowers"]:
                print(f"  • {follower['login']} - {follower['htmlUrl']}")
        else:
            print("\nNo new followers this time.")
            
        if changes["unfollowers"]:
            print(f"\n👋 Unfollowers ({len(changes['unfollowers'])}):")
            for unfollower in changes["unfollowers"]:
                print(f"  • {unfollower['login']} - {unfollower['htmlUrl']}")
        else:
            print("\nNobody unfollowed you. Nice!")
            
        print(f"\nYou have {changes['totalFollowers']} total followers")
        
    elif args.stats:
        stats = tracker.getStats()
        print(f"\n📊 Follower Stats for {args.username}:")
        print(f"  • Total Followers: {stats['totalFollowers']}")
        print(f"  • New Followers Ever: {stats['totalNewFollowers']}")
        print(f"  • Unfollowers Ever: {stats['totalUnfollowers']}")
        
        if stats['recentNewFollowers']:
            print("\n🆕 Recent New Followers:")
            for follower in stats['recentNewFollowers']:
                print(f"  • {follower['user']['login']} - {follower['timestamp']}")
                
        if stats['recentUnfollowers']:
            print("\n🔄 Recent Unfollowers:")
            for unfollower in stats['recentUnfollowers']:
                print(f"  • {unfollower['user']['login']} - {unfollower['timestamp']}")
    else:
        print("Hey! You need to use --check or --stats")
        print("Example: python script.py yourname --check")

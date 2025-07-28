import streamlit as st
import requests
import json
import time
import os
from datetime import datetime
import logging

class GitHubTracker:
    """A class to track GitHub followers, unfollowers, and non-mutual following."""
    
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
                    st.error("Rate limit exceeded. Try using a token or waiting.")
                elif response.status_code == 401:
                    logging.error("Invalid token. Please check your GitHub token.")
                    st.error("Invalid token. Please check your GitHub token.")
                else:
                    logging.error(f"Error getting followers: {response.status_code} - {response.text}")
                    st.error(f"Error getting followers: {response.status_code}")
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
    
    def getFollowing(self):
        """Fetch all users the target user is following.
        
        Returns:
            list: List of following user dictionaries with login, id, avatar_url, and html_url.
        """
        following = []
        page = 1
        
        while True:
            url = f"https://api.github.com/users/{self.username}/following?page={page}&per_page=100"
            response = requests.get(url, headers=self.headers)
            
            self.check_rate_limit(response)
            
            if response.status_code != 200:
                if response.status_code == 403:
                    logging.error("Rate limit exceeded. Try using a token or waiting.")
                    st.error("Rate limit exceeded. Try using a token or waiting.")
                elif response.status_code == 401:
                    logging.error("Invalid token. Please check your GitHub token.")
                    st.error("Invalid token. Please check your GitHub token.")
                else:
                    logging.error(f"Error getting following: {response.status_code} - {response.text}")
                    st.error(f"Error getting following: {response.status_code}")
                return []
            
            pageFollowing = response.json()
            if not pageFollowing:
                break
                
            following.extend([{
                'login': user['login'],
                'id': user['id'],
                'avatarUrl': user['avatar_url'],
                'htmlUrl': user['html_url']
            } for user in pageFollowing])
            
            page += 1
            time.sleep(1)
        
        logging.info(f"Fetched {len(following)} following for {self.username}")
        return following
    
    def getNonMutualFollowing(self):
        """Find users that the target user follows but who don't follow back.
        
        Returns:
            list: List of non-mutual following users.
        """
        followers = self.getFollowers()
        following = self.getFollowing()
        
        follower_usernames = set(user['login'] for user in followers)
        non_mutual = [user for user in following if user['login'] not in follower_usernames]
        
        logging.info(f"Found {len(non_mutual)} non-mutual following for {self.username}")
        return non_mutual
    
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
        
        currentUsernames = set(user['login'] for user in currentFollowers)
        previousUsernames = set(user['login'] for user in previousFollowers)
        
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

def main():
    st.title("GitHub Follower Tracker")
    
    # Initialize session state
    if 'tracker' not in st.session_state:
        st.session_state.tracker = None
        st.session_state.view = 'input'

    # Input form
    if st.session_state.view == 'input':
        st.subheader("Enter GitHub Details")
        username = st.text_input("GitHub Username", key="username")
        token = st.text_input("GitHub Token (optional)", type="password", key="token")
        
        if st.button("Start Tracking"):
            if not username.strip():
                st.error("Please enter a valid GitHub username")
                return
            if token and len(token) < 40:
                st.error("Token seems invalid. Please check or leave it empty.")
                return
            try:
                st.session_state.tracker = GitHubTracker(username, token)
                st.session_state.view = 'menu'
                st.rerun()
            except ValueError as e:
                st.error(f"Error: {e}")
    
    # Main menu
    elif st.session_state.view == 'menu':
        st.subheader(f"Welcome, {st.session_state.tracker.username}")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Check New Followers/Unfollowers"):
                st.session_state.view = 'changes'
                st.rerun()
        with col2:
            if st.button("View Stats"):
                st.session_state.view = 'stats'
                st.rerun()
        with col3:
            if st.button("View Non-Mutual Following"):
                st.session_state.view = 'nonMutual'
                st.rerun()
        
        if st.button("Change User"):
            st.session_state.tracker = None
            st.session_state.view = 'input'
            st.rerun()
    
    # Changes view
    elif st.session_state.view == 'changes':
        st.subheader("Follower Changes")
        with st.spinner("Checking for changes..."):
            changes = st.session_state.tracker.checkChanges()
        
        if changes["newFollowers"]:
            st.markdown(f"### 🎉 New Followers ({len(changes['newFollowers'])})")
            for follower in changes["newFollowers"]:
                st.markdown(f"- [{follower['login']}]({follower['htmlUrl']})")
        else:
            st.write("No new followers this time.")
        
        if changes["unfollowers"]:
            st.markdown(f"### 👋 Unfollowers ({len(changes['unfollowers'])})")
            for unfollower in changes["unfollowers"]:
                st.markdown(f"- [{unfollower['login']}]({unfollower['htmlUrl']})")
        else:
            st.write("Nobody unfollowed you. Nice!")
        
        st.write(f"**Total Followers:** {changes['totalFollowers']}")
        
        if st.button("Back to Menu"):
            st.session_state.view = 'menu'
            st.rerun()
    
    # Stats view
    elif st.session_state.view == 'stats':
        st.subheader(f"Follower Stats for {st.session_state.tracker.username}")
        stats = st.session_state.tracker.getStats()
        
        st.write(f"**Total Followers:** {stats['totalFollowers']}")
        st.write(f"**New Followers Ever:** {stats['totalNewFollowers']}")
        st.write(f"**Unfollowers Ever:** {stats['totalUnfollowers']}")
        
        if stats['recentNewFollowers']:
            st.markdown("### 🆕 Recent New Followers")
            for follower in stats['recentNewFollowers']:
                st.markdown(f"- [{follower['user']['login']}]({follower['user']['htmlUrl']}) - {follower['timestamp']}")
        
        if stats['recentUnfollowers']:
            st.markdown("### 🔄 Recent Unfollowers")
            for unfollower in stats['recentUnfollowers']:
                st.markdown(f"- [{unfollower['user']['login']}]({unfollower['user']['htmlUrl']}) - {unfollower['timestamp']}")
        
        if st.button("Back to Menu"):
            st.session_state.view = 'menu'
            st.rerun()
    
    # Non-mutual view
    elif st.session_state.view == 'nonMutual':
        st.subheader("Non-Mutual Following")
        with st.spinner("Checking non-mutual following..."):
            non_mutual = st.session_state.tracker.getNonMutualFollowing()
        
        if non_mutual:
            st.markdown(f"### 👤 Users you follow but who don’t follow you back ({len(non_mutual)})")
            for user in non_mutual:
                st.markdown(f"- [{user['login']}]({user['htmlUrl']})")
        else:
            st.write("All users you follow also follow you back!")
        
        if st.button("Back to Menu"):
            st.session_state.view = 'menu'
            st.rerun()

if __name__ == "__main__":
    main()

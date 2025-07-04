import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


class TicketDataProcessor:
    """Processes and analyzes support ticket data."""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = None
        self.processed_df = None
        self.vectorizer = None
        self.clusters = None
        
    def load_data(self) -> pd.DataFrame:
        """Load ticket data from CSV file."""
        try:
            for encoding in ['utf-8', 'latin-1', 'cp1251', 'cp1252']:
                try:
                    self.df = pd.read_csv(self.csv_path, encoding=encoding)
                    return self.df
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    continue
            return pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
    
    def clean_data(self) -> pd.DataFrame:
        """Clean and preprocess the data."""
        if self.df is None:
            return pd.DataFrame()
            
        # Create a copy for processing
        df = self.df.copy()
        
        # Fill NaN values with empty strings for text columns
        text_columns = ['Description', 'Last notes', 'Subject']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna('')
        
        # Convert date columns with improved parsing
        date_columns = ['Created', 'Updated', 'Closed', 'Start date', 'Due date']
        for col in date_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], format='%m/%d/%Y %I:%M %p', errors='coerce')
                    if df[col].isna().all():
                        df[col] = pd.to_datetime(df[col], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                    if df[col].isna().all():
                        df[col] = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')
                    if df[col].isna().all():
                        df[col] = pd.to_datetime(df[col], format='%m/%d/%Y', errors='coerce')
                    if df[col].isna().all():
                        df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
                    if df[col].isna().all():
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception:
                    df[col] = pd.NaT
        
        # Clean priority and status columns
        if 'Priority' in df.columns:
            df['Priority'] = df['Priority'].fillna('Normal')
        if 'Status' in df.columns:
            df['Status'] = df['Status'].fillna('Unknown')
            
        # Create combined text field for analysis
        df['combined_text'] = (
            df['Subject'].fillna('') + ' ' + 
            df['Description'].fillna('') + ' ' + 
            df['Last notes'].fillna('')
        ).str.strip()
        
        # Calculate days open
        # For closed tickets: Closed - Created
        # For open tickets: Current date - Created
        current_date = pd.Timestamp.now()
        
        # Use Closed date if available, otherwise use current date
        end_date = df['Closed'].fillna(current_date)
        
        # Calculate days open
        df['days_open'] = (
            (end_date - df['Created']).dt.days
        ).fillna(0)
        
        # Ensure non-negative values
        df['days_open'] = df['days_open'].clip(lower=0)
        
        # Fix value_counts on numpy arrays
        if 'Status' in df.columns and not hasattr(df['Status'], 'value_counts'):
            df['Status'] = pd.Series(df['Status'])
        if 'Priority' in df.columns and not hasattr(df['Priority'], 'value_counts'):
            df['Priority'] = pd.Series(df['Priority'])
        if 'Project' in df.columns and not hasattr(df['Project'], 'value_counts'):
            df['Project'] = pd.Series(df['Project'])
        if 'Tracker' in df.columns and not hasattr(df['Tracker'], 'value_counts'):
            df['Tracker'] = pd.Series(df['Tracker'])
        
        self.processed_df = df
        return df
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in the support tickets."""
        if self.processed_df is None:
            return {}
            
        df = self.processed_df
        
        # Ensure value_counts is called on Series
        status_series = pd.Series(df['Status']) if not hasattr(df['Status'], 'value_counts') else df['Status']
        priority_series = pd.Series(df['Priority']) if not hasattr(df['Priority'], 'value_counts') else df['Priority']
        project_series = pd.Series(df['Project']) if not hasattr(df['Project'], 'value_counts') else df['Project']
        tracker_series = pd.Series(df['Tracker']) if not hasattr(df['Tracker'], 'value_counts') else df['Tracker']
        
        analysis = {
            'total_tickets': len(df),
            'status_distribution': status_series.value_counts().to_dict(),
            'priority_distribution': priority_series.value_counts().to_dict(),
            'project_distribution': project_series.value_counts().to_dict(),
            'tracker_distribution': tracker_series.value_counts().to_dict(),
            'avg_days_open': df['days_open'].mean(),
            'urgent_tickets': len(df[df['Priority'] == 'Urgent']),
            'new_tickets': len(df[df['Status'] == 'New']),
            'closed_tickets': len(df[df['Status'] == 'Solved']),
        }
        
        # Top assignees
        if 'Assignee' in df.columns:
            assignee_series = pd.Series(df['Assignee']) if not hasattr(df['Assignee'], 'value_counts') else df['Assignee']
            analysis['top_assignees'] = assignee_series.value_counts().head(5).to_dict()
            
        # Recent trends (last 30 days)
        if 'Created' in df.columns:
            recent = df[df['Created'] > (datetime.now() - pd.Timedelta(days=30))]
            analysis['recent_tickets'] = len(recent)
            
        return analysis
    
    def cluster_tickets(self, n_clusters: int = 5) -> Dict[str, Any]:
        """Cluster tickets based on their content."""
        if self.processed_df is None:
            return {}
            
        # Filter out empty text
        df = self.processed_df[self.processed_df['combined_text'].str.len() > 0].copy()
        
        if len(df) < n_clusters:
            return {'error': 'Not enough tickets for clustering'}
            
        # Vectorize text
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        try:
            X = self.vectorizer.fit_transform(df['combined_text'])
            
            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            df['cluster'] = kmeans.fit_predict(X)
            self.clusters = kmeans
            
            # Analyze clusters
            cluster_analysis = {}
            for i in range(n_clusters):
                cluster_tickets = df[df['cluster'] == i]
                cluster_analysis[f'cluster_{i}'] = {
                    'size': len(cluster_tickets),
                    'top_subjects': cluster_tickets['Subject'].value_counts().head(3).to_dict() if len(cluster_tickets) > 0 else {},
                    'priority_dist': cluster_tickets['Priority'].value_counts().to_dict() if len(cluster_tickets) > 0 else {},
                    'status_dist': cluster_tickets['Status'].value_counts().to_dict() if len(cluster_tickets) > 0 else {},
                }
                
                # Get representative terms for this cluster
                cluster_center = kmeans.cluster_centers_[i]
                feature_names = self.vectorizer.get_feature_names_out()
                top_indices = cluster_center.argsort()[-10:][::-1]
                cluster_analysis[f'cluster_{i}']['top_terms'] = [
                    feature_names[idx] for idx in top_indices
                ]
            
            return cluster_analysis
            
        except Exception as e:
            return {'error': f'Clustering failed: {e}'}
    
    def get_ticket_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific ticket by ID."""
        if self.processed_df is None:
            return None
            
        ticket = self.processed_df[self.processed_df['#'] == ticket_id]
        if len(ticket) == 0:
            return None
            
        return ticket.iloc[0].to_dict()
    
    def search_tickets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search tickets by text query."""
        if self.processed_df is None:
            return []
            
        # Simple text search
        mask = (
            self.processed_df['combined_text'].str.contains(query, case=False, na=False) |
            self.processed_df['Subject'].str.contains(query, case=False, na=False)
        )
        
        results = self.processed_df[mask].head(limit)
        return results.to_dict('records')
    
    def get_priority_tickets(self, priority: str = 'Urgent') -> List[Dict[str, Any]]:
        """Get tickets by priority level."""
        if self.processed_df is None:
            return []
            
        priority_tickets = self.processed_df[
            self.processed_df['Priority'] == priority
        ].sort_values('Created', ascending=False)
        
        return priority_tickets.to_dict('records')
    
    def get_tickets_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get tickets by status."""
        if self.processed_df is None:
            return []
            
        status_tickets = self.processed_df[
            self.processed_df['Status'] == status
        ].sort_values('Created', ascending=False)
        
        return status_tickets.to_dict('records') 
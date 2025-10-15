#!/usr/bin/env python3
"""
Automatic cleanup of old incident files and videos
Removes files older than configured retention period (default: 30 days)
"""

import os
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class IncidentCleanup:
    """Manages cleanup of old incident files and videos"""
    
    def __init__(self, retention_days=30):
        self.retention_days = retention_days
        self.base_dir = Path.cwd()
        
        # Directories to clean
        self.offline_incidents_dir = self.base_dir / 'offline_incidents'
        self.mock_videos_dir = self.base_dir / 'mock_sparse_ai_cloud'
        
    def cleanup_old_files(self, directory, file_pattern='*', dry_run=False):
        """
        Remove files older than retention period
        
        Args:
            directory: Directory to clean
            file_pattern: Glob pattern for files to clean (default: all files)
            dry_run: If True, only report what would be deleted
            
        Returns:
            dict: Statistics about cleanup operation
        """
        if not directory.exists():
            logger.info(f"Directory does not exist: {directory}")
            return {
                'found': 0,
                'deleted': 0,
                'errors': 0,
                'total_size_mb': 0,
                'freed_size_mb': 0
            }
        
        cutoff_time = time.time() - (self.retention_days * 24 * 60 * 60)
        cutoff_date = datetime.fromtimestamp(cutoff_time)
        
        stats = {
            'found': 0,
            'deleted': 0,
            'errors': 0,
            'total_size_mb': 0,
            'freed_size_mb': 0
        }
        
        logger.info(f"Scanning {directory} for files older than {cutoff_date.strftime('%Y-%m-%d')}")
        
        for file_path in directory.glob(file_pattern):
            if not file_path.is_file():
                continue
                
            stats['found'] += 1
            file_mtime = file_path.stat().st_mtime
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            stats['total_size_mb'] += file_size_mb
            
            if file_mtime < cutoff_time:
                file_age_days = (time.time() - file_mtime) / (24 * 60 * 60)
                
                if dry_run:
                    logger.info(f"Would delete (age: {file_age_days:.1f} days, size: {file_size_mb:.2f} MB): {file_path.name}")
                else:
                    try:
                        file_path.unlink()
                        stats['deleted'] += 1
                        stats['freed_size_mb'] += file_size_mb
                        logger.info(f"Deleted (age: {file_age_days:.1f} days, size: {file_size_mb:.2f} MB): {file_path.name}")
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"Failed to delete {file_path.name}: {e}")
        
        return stats
    
    def cleanup_offline_incidents(self, dry_run=False):
        """Clean up old offline incident files"""
        logger.info(f"\n{'DRY RUN: ' if dry_run else ''}Cleaning up offline incident files...")
        logger.info(f"Retention period: {self.retention_days} days")
        
        stats = self.cleanup_old_files(
            self.offline_incidents_dir,
            file_pattern='offline_incident_*.txt',
            dry_run=dry_run
        )
        
        logger.info(f"\nOffline Incidents Cleanup Summary:")
        logger.info(f"  Total files found: {stats['found']}")
        logger.info(f"  Files {'to be ' if dry_run else ''}deleted: {stats['deleted']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info(f"  Total size: {stats['total_size_mb']:.2f} MB")
        logger.info(f"  Space {'to be ' if dry_run else ''}freed: {stats['freed_size_mb']:.2f} MB")
        
        return stats
    
    def cleanup_mock_videos(self, dry_run=False):
        """Clean up old mock service videos"""
        logger.info(f"\n{'DRY RUN: ' if dry_run else ''}Cleaning up mock service videos...")
        logger.info(f"Retention period: {self.retention_days} days")
        
        # Clean both .mp4 and .json files
        video_stats = self.cleanup_old_files(
            self.mock_videos_dir,
            file_pattern='*.mp4',
            dry_run=dry_run
        )
        
        json_stats = self.cleanup_old_files(
            self.mock_videos_dir,
            file_pattern='*.json',
            dry_run=dry_run
        )
        
        # Combine stats
        stats = {
            'found': video_stats['found'] + json_stats['found'],
            'deleted': video_stats['deleted'] + json_stats['deleted'],
            'errors': video_stats['errors'] + json_stats['errors'],
            'total_size_mb': video_stats['total_size_mb'] + json_stats['total_size_mb'],
            'freed_size_mb': video_stats['freed_size_mb'] + json_stats['freed_size_mb']
        }
        
        logger.info(f"\nMock Videos Cleanup Summary:")
        logger.info(f"  Total files found: {stats['found']} ({video_stats['found']} videos, {json_stats['found']} metadata)")
        logger.info(f"  Files {'to be ' if dry_run else ''}deleted: {stats['deleted']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info(f"  Total size: {stats['total_size_mb']:.2f} MB")
        logger.info(f"  Space {'to be ' if dry_run else ''}freed: {stats['freed_size_mb']:.2f} MB")
        
        return stats
    
    def cleanup_all(self, dry_run=False):
        """Clean up all old files"""
        logger.info("="*70)
        logger.info(f"{'DRY RUN: ' if dry_run else ''}AUTOMATIC CLEANUP - Retention: {self.retention_days} days")
        logger.info("="*70)
        
        incident_stats = self.cleanup_offline_incidents(dry_run=dry_run)
        video_stats = self.cleanup_mock_videos(dry_run=dry_run)
        
        total_deleted = incident_stats['deleted'] + video_stats['deleted']
        total_freed = incident_stats['freed_size_mb'] + video_stats['freed_size_mb']
        
        logger.info("\n" + "="*70)
        logger.info("TOTAL CLEANUP SUMMARY")
        logger.info("="*70)
        logger.info(f"Files {'to be ' if dry_run else ''}deleted: {total_deleted}")
        logger.info(f"Space {'to be ' if dry_run else ''}freed: {total_freed:.2f} MB")
        logger.info("="*70)
        
        return {
            'incidents': incident_stats,
            'videos': video_stats,
            'total_deleted': total_deleted,
            'total_freed_mb': total_freed
        }


def main():
    """Main entry point for cleanup script"""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(
        description='Clean up old incident files and videos'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Retention period in days (default: 30)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--incidents-only',
        action='store_true',
        help='Only clean up incident files'
    )
    parser.add_argument(
        '--videos-only',
        action='store_true',
        help='Only clean up videos'
    )
    
    args = parser.parse_args()
    
    cleanup = IncidentCleanup(retention_days=args.days)
    
    if args.incidents_only:
        cleanup.cleanup_offline_incidents(dry_run=args.dry_run)
    elif args.videos_only:
        cleanup.cleanup_mock_videos(dry_run=args.dry_run)
    else:
        cleanup.cleanup_all(dry_run=args.dry_run)


if __name__ == '__main__':
    main()

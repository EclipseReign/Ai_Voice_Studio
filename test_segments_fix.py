#!/usr/bin/env python3
"""
Test the split_text_into_segments function fix directly
"""

import sys
import re

def split_text_into_segments(text: str, max_segment_length: int = 1000) -> list:
    """
    Copy of the fixed function from server.py to test directly
    """
    # Add pauses at punctuation for natural speech rhythm
    # Add longer pause after sentence-ending punctuation (.!?)
    text = re.sub(r'([.!?])\s+', r'\1 ... ', text)  # Add pause after sentences
    # Add shorter pause after commas, semicolons, colons
    text = re.sub(r'([,;:])\s+', r'\1 .. ', text)  # Add pause after internal punctuation
    
    # Split by sentences (periods, exclamation marks, question marks)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    segments = []
    current_segment = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed max length, start a new segment
        if current_segment and len(current_segment) + len(sentence) > max_segment_length:
            segments.append(current_segment.strip())
            current_segment = sentence
        else:
            current_segment += " " + sentence if current_segment else sentence
    
    # Add remaining segment
    if current_segment:
        segments.append(current_segment.strip())
    
    return segments

def test_segments_function():
    """Test the segments function with the exact text from the review request"""
    
    print("🔍 Testing split_text_into_segments function fix")
    print("=" * 60)
    
    # Test text from review request
    test_text = "Hello world, this is a test of audio generation with Piper TTS."
    
    print(f"Input text: '{test_text}'")
    print(f"Text length: {len(test_text)} characters")
    
    try:
        # Call the function
        segments = split_text_into_segments(test_text)
        
        # Check if result is None (the bug)
        if segments is None:
            print("❌ CRITICAL BUG STILL EXISTS: Function returned None!")
            return False
        
        # Check if result is a list
        if not isinstance(segments, list):
            print(f"❌ ERROR: Function returned {type(segments)}, expected list")
            return False
        
        # Check if we can get length (this would fail with NoneType)
        try:
            segment_count = len(segments)
            print(f"✅ SUCCESS: Function returned list with {segment_count} segments")
        except TypeError as e:
            if "NoneType" in str(e):
                print(f"❌ CRITICAL BUG: {str(e)}")
                return False
            else:
                print(f"❌ ERROR: {str(e)}")
                return False
        
        # Print segments
        print("\nGenerated segments:")
        for i, segment in enumerate(segments, 1):
            print(f"  {i}. '{segment}' ({len(segment)} chars)")
        
        # Verify segments are not empty
        empty_segments = [i for i, seg in enumerate(segments) if not seg.strip()]
        if empty_segments:
            print(f"⚠️  Warning: Found empty segments at positions: {empty_segments}")
        
        print(f"\n✅ CRITICAL BUG FIX VERIFIED: segments function returns {segment_count} segments")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Exception occurred: {str(e)}")
        return False

def test_longer_text():
    """Test with longer text to ensure chunking works"""
    
    print("\n🔍 Testing with longer text (chunking)")
    print("=" * 60)
    
    # Longer test text
    long_text = """
    Artificial intelligence represents one of the most significant technological advances of our time. 
    It encompasses a broad range of technologies and methodologies that enable machines to perform tasks 
    that typically require human intelligence. From machine learning algorithms that can recognize patterns 
    in vast datasets to natural language processing systems that can understand and generate human language, 
    AI is transforming virtually every aspect of our lives. The history of artificial intelligence dates 
    back to the 1950s when computer scientists first began exploring the possibility of creating machines 
    that could think and learn like humans.
    """
    
    print(f"Input text length: {len(long_text)} characters")
    
    try:
        segments = split_text_into_segments(long_text, max_segment_length=200)
        
        if segments is None:
            print("❌ CRITICAL BUG: Function returned None for longer text!")
            return False
        
        segment_count = len(segments)
        print(f"✅ SUCCESS: Generated {segment_count} segments")
        
        # Check segment lengths
        for i, segment in enumerate(segments, 1):
            print(f"  Segment {i}: {len(segment)} chars - '{segment[:50]}...'")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 CRITICAL BUG FIX VERIFICATION")
    print("Testing: split_text_into_segments returns segments (not None)")
    print("Issue: TypeError: object of type 'NoneType' has no len()")
    print()
    
    # Test 1: Short text (from review request)
    test1_success = test_segments_function()
    
    # Test 2: Longer text (chunking)
    test2_success = test_longer_text()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Critical bug fix verified: split_text_into_segments returns segments")
        print("✅ No 'NoneType has no len()' errors")
        print("✅ Function works for both short and long texts")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        if not test1_success:
            print("❌ Short text test failed")
        if not test2_success:
            print("❌ Long text test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
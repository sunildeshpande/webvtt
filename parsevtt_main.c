/**
 * Copyright (c) 2013 Mozilla Foundation and Contributors
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met:
 *
 *  - Redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer.
 *  - Redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include <webvtt/parser.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <ctype.h>

typedef struct sentiment_ctx {
  const char *filename;
  int cues_processed;
  int total_score;
  int positive_matches;
  int negative_matches;
} sentiment_ctx;

typedef struct sentiment_result {
  int score;
  int positive_matches;
  int negative_matches;
  int total_words;
} sentiment_result;

static const char *const POSITIVE_WORDS[] = {
  "good", "great", "excellent", "amazing", "happy", "joy", "love", "fantastic",
  "positive", "success", "enjoy", "wonderful", "smile", "delight", "peace",
  "win", "friendly", "brilliant", "calm", "progress", 0
};

static const char *const NEGATIVE_WORDS[] = {
  "bad", "terrible", "awful", "sad", "angry", "hate", "horrible", "negative",
  "fail", "failure", "worse", "worst", "pain", "fear", "problem", "loss",
  "cry", "danger", "frustrated", "stress", 0
};

static int
word_in_list( const char *word, const char *const *list )
{
  while( list && *list ) {
    if( strcmp( word, *list ) == 0 ) {
      return 1;
    }
    ++list;
  }
  return 0;
}

static void
flush_word( const char *word, sentiment_result *result )
{
  if( !word || !*word ) {
    return;
  }
  ++result->total_words;
  if( word_in_list( word, POSITIVE_WORDS ) ) {
    ++result->positive_matches;
    ++result->score;
  } else if( word_in_list( word, NEGATIVE_WORDS ) ) {
    ++result->negative_matches;
    --result->score;
  }
}

static sentiment_result
analyze_sentiment( const char *text )
{
  sentiment_result result = { 0 };
  char token[64];
  int idx = 0;
  if( !text ) {
    return result;
  }
  while( *text ) {
    unsigned char ch = (unsigned char)*text;
    if( isalpha( ch ) ) {
      if( idx < (int)sizeof( token ) - 1 ) {
        token[idx++] = (char)tolower( ch );
      }
    } else if( idx ) {
      token[idx] = 0;
      flush_word( token, &result );
      idx = 0;
    }
    ++text;
  }
  if( idx ) {
    token[idx] = 0;
    flush_word( token, &result );
  }
  return result;
}

static int WEBVTT_CALLBACK
error( void *userdata, webvtt_uint line, webvtt_uint col, webvtt_error errcode )
{
  sentiment_ctx *ctx = (sentiment_ctx *)userdata;
  const char *label = ( ctx && ctx->filename ) ? ctx->filename : "input";
  fprintf(stderr, "`%s' at %u:%u -- error: %s\n", label, line, col, webvtt_strerror( errcode ) );
  return -1; /* Die on all errors */
}

static void WEBVTT_CALLBACK
cue( void *userdata, webvtt_cue *cue )
{
  sentiment_ctx *ctx = (sentiment_ctx *)userdata;
  const char *body = webvtt_string_text( &cue->body );
  sentiment_result result = analyze_sentiment( body );

  if( ctx ) {
    ++ctx->cues_processed;
    ctx->total_score += result.score;
    ctx->positive_matches += result.positive_matches;
    ctx->negative_matches += result.negative_matches;
  }

  printf( "Cue %d: \"%s\"\n", ctx ? ctx->cues_processed : 0, body ? body : "" );
  printf( "  Sentiment score: %d (positive %d / negative %d)\n",
          result.score, result.positive_matches, result.negative_matches );
}

int
parse_fh(FILE *fh, webvtt_parser vtt)
{
  /**
   * Try to parse the file.
   */
  int finished;
  webvtt_status result;
  do {
    char buffer[0x1000];
    webvtt_uint n_read = (webvtt_uint)fread( buffer, 1, sizeof(buffer), fh );
    finished = feof( fh );
    if( WEBVTT_FAILED(result = webvtt_parse_chunk( vtt, buffer, n_read )) ) {
      return 1;
    }
  } while( !finished && result == WEBVTT_SUCCESS );
  webvtt_finish_parsing( vtt );
  
  return 0;
}

int
main( int argc, char **argv )
{
  const char *input_file = 0;
  webvtt_status result;
  webvtt_parser vtt;

//  webvtt_node *mHead = NULL;
  FILE *fh;
  int i;
  int ret = 0;
  for( i = 0; i < argc; ++i ) {
    const char *a = argv[i];
    if( *a == '-' ) {
      switch( a[1] ) {
        case 'f': {
          const char *p = a + 2;
          while( isspace(*p) ) { ++p; }
          if( *p ) {
            input_file = p;
          } else if( i + 1 < argc ) {
            input_file = argv[i + 1];
            ++i;
          } else {
            fprintf( stderr, "error: missing parameter for switch `-f'\n" );
          }
        }
        break;

        case '?': {
          fprintf( stdout, "Usage: parsevtt -f <vttfile>\n" );
          return 0;
        }
        break;
      }
    }
  }
  if( !input_file ) {
    fprintf( stderr, "error: missing input file.\n\nUsage: parsevtt -f <vttfile>\n" );
    return 1;
  }

  fh = fopen(input_file, "rb");
  if( !fh ) {
    fprintf( stderr, "error: failed to open `%s'"
#ifdef WEBVTT_HAVE_STRERROR
             ": %s"
#endif
             "\n", input_file
#ifdef WEBVTT_HAVE_STRERROR
             , strerror(errno)
#endif
           );
    return 1;
  }

//  webvtt_init_node(&mHead);
  sentiment_ctx ctx;
  memset( &ctx, 0, sizeof( ctx ) );
  ctx.filename = input_file;

  if( ( result = webvtt_create_parser( &cue, &error, (void *)&ctx, &vtt ) ) != WEBVTT_SUCCESS ) {
    fprintf( stderr, "error: failed to create VTT parser.\n" );
    fclose( fh );
    return 1;
  }

  ret = parse_fh( fh, vtt );
#if 0
  webvtt_ref_node(mHead);
  // mHead should actually be the head of a node tree.

  if (!mHead || mHead->kind != WEBVTT_HEAD_NODE) {
     printf(" mHead node is null\n");
     return  -1;
     }
  switch (mHead->kind) {
    case WEBVTT_BOLD:
      printf("BOLD\n");
      //atom = nsGkAtoms::b;
      break;

    case WEBVTT_ITALIC:
      printf("ITALIC\n");
      //atom = nsGkAtoms::i;
      break;

    case WEBVTT_UNDERLINE:
      printf("UNDERLINE\n");
      //atom = nsGkAtoms::u;
      break;

    case WEBVTT_RUBY:
      printf("RUBY\n");
      //atom = nsGkAtoms::ruby;
      break;

    case WEBVTT_RUBY_TEXT:
      printf("RUBY_TEXT\n");
      //atom = nsGkAtoms::rt;
      break;

    case WEBVTT_VOICE:
      printf("VOICE\n");
      //atom = nsGkAtoms::span;
      break;

    case WEBVTT_CLASS:
      printf("CLASS\n");
      //atom = nsGkAtoms::span;
      break;

    default:
      //return NULL;
      break;

  }
#endif


  webvtt_delete_parser( vtt );
  fclose( fh );

  if( ctx.cues_processed > 0 ) {
    double avg = (double)ctx.total_score / (double)ctx.cues_processed;
    printf( "\nProcessed %d cues from `%s`\n", ctx.cues_processed, input_file );
    printf( "Aggregate sentiment score: %d\n", ctx.total_score );
    printf( "Average sentiment per cue: %.2f\n", avg );
    printf( "Positive matches: %d | Negative matches: %d\n",
            ctx.positive_matches, ctx.negative_matches );
  } else {
    printf( "\nNo cues were parsed from `%s`.\n", input_file );
  }
  return ret;
}

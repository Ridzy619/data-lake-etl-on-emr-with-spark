import configparser
from datetime import datetime
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.functions import year, month, dayofmonth, hour, weekofyear, date_format


config = configparser.ConfigParser()
config.read('dl.cfg')

os.environ['AWS_ACCESS_KEY_ID']=config['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY']=config['AWS_SECRET_ACCESS_KEY']


def create_spark_session():
    '''
    Create a spark connection that includes hadoop packages
    
    return:
        spark instance
    '''
    spark = SparkSession \
        .builder \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:2.7.0") \
        .getOrCreate()
    return spark


def process_song_data(spark, input_data, output_data):
    '''
    Process and save song data as new tables in parquet format
    '''
    # get filepath to song data file
    song_data = input_data + '/song_data'
    
    # read song data file
    df = spark.read.json(song_data)

    # extract columns to create songs table
    songs_table = df.select(['song_id', 'title', 'artist_id', 'year', 'duration'])
    
    # write songs table to parquet files partitioned by year and artist
    songs_table.write.partitionBy('year', 'artist_id').parquet(output_data + '/songs_data', mode='overwrite')

    # extract columns to create artists table
    artists_table = df.select(['artist_id', 'artist_name', 'artist_location', 'artist_latitude', 'artist_longitude'])
    
    # write artists table to parquet files
    artists_table.write.parquet(output_data + '/artists_table', mode='overwrite')
    
    
def process_log_data(spark, input_data, output_data):
    '''
    Process and save song data as new tables in parquet format
    '''
    from pyspark.sql import functions as F
    from pyspark.sql import types as T
    # get filepath to log data file
    log_data = input_data + '/log_data'

    # read log data file
    df = spark.read.json(log_data)
    
    # filter by actions for song plays
    df = df.where(F.col('page')==('NextSong'))

    # extract columns for users table    
    users_table = df.select([
        F.col('userId').alias('user_id'),
        F.col('firstName').alias('first_name'),
        F.col('lastName').alias('last_name'),
        'gender',
        'level'
    ])
    
    # write users table to parquet files
    users_table.write.parquet(output_data + '/users_table', mode='overwrite')
    
    # extract columns to create time table
    time_table = df\
        .select(F.from_unixtime(F.col('ts')/1000).alias('ts'))\
        .select(
            F.hour('ts').alias('hour'),
            F.dayofyear('ts').alias('day'),
            F.weekofyear('ts').alias('week'),
            F.month('ts').alias('month'),
            F.year('ts').alias('year'),
            F.date_format('ts', 'u').alias('weekday')
        )

    
    # write time table to parquet files partitioned by year and month
    time_table.write.partitionBy(['year', 'month']).parquet(output_data + '/time_table', mode='overwrite')

    # read in song data to use for songplays table
    song_df = spark.read.json(output_data + '/songs_data')

    # extract columns from joined song and log datasets to create songplays table 
    cols = [
        F.row_number().over(Window.partitionBy().orderBy(F.current_timestamp())).alias('songplay_id'),
        F.from_unixtime(F.col('ts')/1000).alias('ts').alias('start_time'),
        F.col('userId').alias('user_id'),
        'level',
        'song_id',
        'artist_id',
        F.col('sessionId').alias('session_id'),
        'location',
        F.col('userAgent').alias('user_agent'),
    ]
    songplays_table = df\
        .join(songs_table,
           on=(F.col('song')==songs_table.title) & (F.col('length')==songs_table.duration),
           how='inner')\
        .select(cols)

    # write songplays table to parquet files partitioned by year and month
    songplays_table.withColumn('year', F.year('start_time'))\
        .withColumn('month', F.month('start_time'))\
        .write.partitionBy('year', 'month')\
        .parquet(output_data + 'songplays_table', mode='overwrite')


def main():
    '''
    Run process_song_data and process_log_data functions
    '''
    spark = create_spark_session()
    input_data = "s3a://udacity-dend/"
    output_data = "s3a://uda-spark-data/data/"
    
    process_song_data(spark, input_data, output_data)    
    process_log_data(spark, input_data, output_data)
    
    spark.stop()


if __name__ == "__main__":
    main()
package ai.astrovox.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import ai.astrovox.data.local.converters.Converters
import ai.astrovox.data.local.entities.ConversationEntity
import ai.astrovox.data.local.entities.MessageEntity

@Database(entities = [ConversationEntity::class, MessageEntity::class], version = 1)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun conversationDao(): ConversationDao
    abstract fun messageDao(): MessageDao
}

{-# LANGUAGE OverloadedStrings, DeriveGeneric #-}

module Main where

import qualified Data.ByteString.Lazy as BL
import Data.Csv
import Data.Text (Text)
import qualified Data.Vector as V
import GHC.Generics

newtype DefaultToZero = DefaultToZero Int

-- from http://hackage.haskell.org/package/cassava-0.5.2.0/docs/Data-Csv.html
instance FromField DefaultToZero where -- means DefaultToZero is an instance of FromField
    parseField s = case runParser (parseField s) of
        Left err  -> pure $ DefaultToZero 0
        Right n   -> pure $ DefaultToZero n

-- it looks like I need to define ToNamedRecord too, but I don't understand Instance yet

data Location = Location
    { number          :: !Int
    , description     :: !String
    , level           :: !String
    , locationtype    :: !String
    , variety         :: !String
    , size            :: !Double
    , containedwithin :: !DefaultToZero
    }
    deriving Generic

instance FromNamedRecord Location
instance ToNamedRecord Location
instance DefaultOrdered Location

data Item = Item
     { labelnumber           :: !Int
     , item                  :: !String
     , itemtype              :: !String
     , subtype               :: !String
     , subsubtype            :: !String
     , normallocation        :: !DefaultToZero
     , origin                :: !String
     , acquired              :: !String
     , brand                 :: !String
     , model                 :: !String
     , serialnumber          :: !String
     , usefulness            :: !Double
     , nostalgia             :: !Double
     , fun                   :: !Double
     , approxvaluewhenbought :: !Double
     , condition             :: !String
     , status                :: !String
     } deriving Generic

instance FromNamedRecord Item
instance ToNamedRecord Item
instance DefaultOrdered Item

main :: IO ()
main = do
     locationData <- BL.readFile "data/storage.csv"
     case decodeByName locationData of
          Left err -> putStrLn err
          Right (_ , v) -> V.forM_ v $ \ p ->
                putStrLn $ description p ++ " is within " ++ show (containedwithin p)
     inventoryData <- BL.readFile "data/items.csv"
     case decodeByName inventoryData of
          Left err -> putStrLn err
          Right (_ , v) -> V.forM_ v $ \ p ->
                putStrLn $ description p ++ " is within " ++ show (containedwithin p)

import React from 'react';
import {ScrollView, StyleSheet, FlatList, Text, Alert} from 'react-native';
import { ExpoLinksView } from '@expo/samples';
import { MonoText } from '../components/StyledText';
import { List, ListItem } from "react-native-elements";

const people = [
        {
            name: 'Jen',
            image: '../assets/images/robot-dev.png',
            phone: '647 809 9500'
        },
        {
            name: 'Dan',
            image: '../assets/images/robot-prod.png',
            phone: '647 809 9500'
        },
        {
            name: 'Matt',
            image: '../assets/images/robot-dev.png',
            phone: '647 809 9500'
        },
        {
            name: 'Steve',
            image: '../assets/images/robot-prod.png',
            phone: '647 809 9500'
        },
        {
            name: 'Deborah',
            image: '../assets/images/robot-dev.png',
            phone: '647 809 9500'
        }
];

//TODO look at this when you need to do it for real
//https://medium.com/react-native-development/how-to-use-the-flatlist-component-react-native-basics-92c482816fe6
export default class FriendsListScreen extends React.Component {
  static navigationOptions = {
    title: 'Your Free Friends',
  };

    clickFriend(friend) {
        const url = (Platform.OS === 'android')
            ? 'sms:' + friend.phone + '?body=Hey! I saw you\'re free tonight on Veni. Want to hang out?'
            : 'sms:' + friend.phone;

        Linking.canOpenURL(url).then(supported => {
            if (!supported) {
                console.log('Unsupported url: ' + url)
            } else {
                return Linking.openURL(url)
            }
        }).catch(err => console.error('An error occurred', err))
    }

  render() {
    return (
        <FlatList
            data={people}
            renderItem={({ item }) => (
                <ListItem
                    roundAvatar
                    title={`${item.name}`}
                    subtitle={item.name + "@gmail.com"}
                    avatar={{ uri: item.image}}
                    onPress={() => {this.clickFriend(item)}}
            )}
            keyExtractor={(item, index) => index.toString()}
        />
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 15,
    backgroundColor: '#fff',
  },
});
